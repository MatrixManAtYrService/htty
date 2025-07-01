use crate::nbio;
use anyhow::Result;
use nix::libc;
use nix::pty;
use nix::sys::signal::{self, SigHandler, Signal};
use nix::sys::wait;
use nix::unistd::{self, ForkResult, Pid};
use std::env;
use std::ffi::{CString, NulError};
use std::fs::File;
use std::future::Future;
use std::io::{self};
use std::os::fd::FromRawFd;
use std::os::fd::{AsRawFd, OwnedFd};
use std::path::PathBuf;
use tokio::io::unix::AsyncFd;
use tokio::sync::mpsc;
use crate::command::Command;

pub fn spawn(
    command: String,
    winsize: &pty::Winsize,
    input_rx: mpsc::Receiver<Vec<u8>>,
    output_tx: mpsc::Sender<Vec<u8>>,
    pid_tx: mpsc::Sender<i32>,
    exit_code_tx: mpsc::Sender<i32>,
    command_tx: mpsc::Sender<Command>,
) -> Result<impl Future<Output = Result<()>>> {
    // Generate FIFO path using parent PID (step 1 in desired flow)
    let fifo_path = format!("/tmp/ht_fifo_{}", std::process::id());
    let fifo_path_buf = PathBuf::from(&fifo_path);

    let result = unsafe { pty::forkpty(Some(winsize), None) }?;

    match result.fork_result {
        ForkResult::Parent { child } => {
            let pid = child.as_raw();

            // Add debug event for FIFO path generation
            let _ = pid_tx.try_send(pid);
            
            let command_tx_clone = command_tx.clone();
            let fifo_path_debug = fifo_path.clone();
            tokio::spawn(async move {
                let _ = command_tx_clone.try_send(Command::Debug(format!("fifoPathGenerated:{}", fifo_path_debug)));
            });

            Ok(drive_child(child, result.master, input_rx, output_tx, exit_code_tx, command_tx, fifo_path_buf))
        },

        ForkResult::Child => {
            exec(command, fifo_path)?;
            unreachable!();
        }
    }
}

async fn drive_child(
    child: Pid,
    master: OwnedFd,
    input_rx: mpsc::Receiver<Vec<u8>>,
    output_tx: mpsc::Sender<Vec<u8>>,
    exit_code_tx: mpsc::Sender<i32>,
    command_tx: mpsc::Sender<Command>,
    fifo_path: PathBuf,
) -> Result<()> {
    // Debug event: Starting coordination
    let _ = command_tx.try_send(Command::Debug(format!("startingCoordination:{}", fifo_path.display())));
    
    // Start a task to monitor FIFO existence (step 4-5 in desired flow)
    let fifo_command_tx = command_tx.clone();
    let fifo_path_clone = fifo_path.clone();
    let _monitor_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(50));
        
        // Step 4: Periodically check if FIFO exists
        let _ = fifo_command_tx.try_send(Command::Debug("startingFifoMonitoring".to_string()));
        
        loop {
            interval.tick().await;
            
            // Check if FIFO exists (indicates command completed and waitexit is blocking)
            if fifo_path_clone.exists() {
                let _ = fifo_command_tx.try_send(Command::Completed(fifo_path_clone.clone()));
                break; // Exit monitoring once FIFO is detected
            }
        }
    });

    // Process the main command and capture its output
    let _result = do_drive_child(master, input_rx, output_tx.clone()).await;
    
    // Step 5: Output capture is complete, but don't signal waitexit yet
    let _ = command_tx.try_send(Command::Debug("outputCaptureComplete".to_string()));
    
    eprintln!("sending HUP signal to the child process");
    unsafe { libc::kill(child.as_raw(), libc::SIGHUP) };
    eprintln!("waiting for the child process to exit");

    // After signaling wait-exit, we want to keep the ht process alive for snapshots
    // So we don't return here - we keep the output_tx alive and just wait
    
    // Give waitexit time to process the exit signal and clean up
    tokio::time::sleep(std::time::Duration::from_millis(200)).await;

    // Step 7: waitexit should exit and shell command completes
    let _ = command_tx.try_send(Command::Debug("coordinationComplete".to_string()));

    tokio::task::spawn_blocking(move || {
        match wait::waitpid(child, None) {
            Ok(wait_status) => {
                let exit_code = match wait_status {
                    wait::WaitStatus::Exited(_, code) => code,
                    wait::WaitStatus::Signaled(_, signal, _) => 128 + signal as i32,
                    _ => -1,
                };
                let _ = exit_code_tx.try_send(exit_code);
            }
            Err(_) => {
                let _ = exit_code_tx.try_send(-1);
            }
        }
    })
    .await
    .unwrap();

    // Instead of returning the result which would drop output_tx,
    // we keep the task alive indefinitely to keep ht running for snapshots
    // The output_tx will be kept alive, preventing the main event loop from exiting
    let _ = command_tx.try_send(Command::Debug("ptyContinuingForSnapshots".to_string()));
    
    // Keep this task alive but allow it to exit gracefully when needed
    // We'll send periodic heartbeats but also check if the main process is shutting down
    let mut heartbeat_interval = tokio::time::interval(std::time::Duration::from_secs(60));
    
    loop {
        tokio::select! {
            _ = heartbeat_interval.tick() => {
                // Send a periodic heartbeat to show we're still alive
                if command_tx.try_send(Command::Debug("ptyHeartbeat".to_string())).is_err() {
                    // If we can't send debug commands, the main process is shutting down
                    let _ = command_tx.try_send(Command::Debug("ptyExitingDueToChannelClosure".to_string()));
                    break;
                }
            }
            
            // Add a small delay to prevent busy waiting
            _ = tokio::time::sleep(std::time::Duration::from_millis(100)) => {
                // Check if the main command channel is closed (indicating shutdown)
                if command_tx.is_closed() {
                    let _ = command_tx.try_send(Command::Debug("ptyExitingDueToMainShutdown".to_string()));
                    break;
                }
            }
        }
    }

    let _ = command_tx.try_send(Command::Debug("ptyTaskExiting".to_string()));
    Ok(())
}

const READ_BUF_SIZE: usize = 128 * 1024;

async fn do_drive_child(
    master: OwnedFd,
    mut input_rx: mpsc::Receiver<Vec<u8>>,
    output_tx: mpsc::Sender<Vec<u8>>,
) -> Result<()> {
    let mut buf = [0u8; READ_BUF_SIZE];
    let mut input: Vec<u8> = Vec::with_capacity(READ_BUF_SIZE);
    nbio::set_non_blocking(&master.as_raw_fd())?;
    let mut master_file = unsafe { File::from_raw_fd(master.as_raw_fd()) };
    let master_fd = AsyncFd::new(master)?;

    loop {
        tokio::select! {
            result = input_rx.recv() => {
                match result {
                    Some(data) => {
                        input.extend_from_slice(&data);
                    }

                    None => {
                        return Ok(());
                    }
                }
            }

            result = master_fd.readable() => {
                let mut guard = result?;

                loop {
                    match nbio::read(&mut master_file, &mut buf)? {
                        Some(0) => {
                            return Ok(());
                        }

                        Some(n) => {
                            output_tx.send(buf[0..n].to_vec()).await?;
                        }

                        None => {
                            guard.clear_ready();
                            break;
                        }
                    }
                }
            }

            result = master_fd.writable(), if !input.is_empty() => {
                let mut guard = result?;
                let mut buf: &[u8] = input.as_ref();

                loop {
                    match nbio::write(&mut master_file, buf)? {
                        Some(0) => {
                            return Ok(());
                        }

                        Some(n) => {
                            buf = &buf[n..];

                            if buf.is_empty() {
                                break;
                            }
                        }

                        None => {
                            guard.clear_ready();
                            break;
                        }
                    }
                }

                let left = buf.len();

                if left == 0 {
                    input.clear();
                } else {
                    input.drain(..input.len() - left);
                }
            }
        }
    }
}

fn exec(command: String, fifo_path: String) -> io::Result<()> {
    let ht_binary = env::current_exe()
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?
        .to_string_lossy()
        .to_string();
    
    // Capture the exit code, run wait-exit, then exit with the original code
    let final_command = format!("{} ; exit_code=$? ; {} wait-exit {} ; exit $exit_code", command, ht_binary, fifo_path);


    let shell_path = "/bin/sh";
    let command = [shell_path.to_owned(), "-c".to_owned(), final_command]
        .iter()
        .map(|s| CString::new(s.as_bytes()))
        .collect::<Result<Vec<CString>, NulError>>()?;

    env::set_var("TERM", "xterm-256color");
    unsafe { signal::signal(Signal::SIGPIPE, SigHandler::SigDfl) }?;
    unistd::execvp(&command[0], &command)?;
    unsafe { libc::_exit(1) }
}
