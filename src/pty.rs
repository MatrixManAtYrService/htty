use crate::nbio;
use anyhow::Result;
use nix::libc;
use nix::pty;
use nix::sys::signal::{self, SigHandler, Signal};
use nix::sys::wait;
use nix::unistd::{self, ForkResult, Pid};
use tempfile::NamedTempFile;
use std::env;
use std::ffi::{CString, NulError};
use std::fs::File;
use std::future::Future;
use std::io;
use std::os::fd::FromRawFd;
use std::os::fd::{AsRawFd, OwnedFd};
use tokio::io::unix::AsyncFd;
use tokio::sync::mpsc;

pub fn spawn(
    command: String,
    winsize: &pty::Winsize,
    input_rx: mpsc::Receiver<Vec<u8>>,
    output_tx: mpsc::Sender<Vec<u8>>,
    pid_tx: mpsc::Sender<i32>,
    exit_code_tx: mpsc::Sender<i32>,
    no_exit: bool,
) -> Result<impl Future<Output = Result<()>>> {
    let result = unsafe { pty::forkpty(Some(winsize), None) }?;

    // Create signal file if no_exit is enabled
    let signal_file = if no_exit {
        Some(NamedTempFile::new()?)
    } else {
        None
    };

    match result.fork_result {
        ForkResult::Parent { child } => {
            let pid = child.as_raw();

            tokio::spawn(async move {
                let _ = pid_tx.try_send(pid);
            });

            Ok(drive_child(child, result.master, input_rx, output_tx, exit_code_tx, signal_file))
        },

        ForkResult::Child => {
            let signal_file_path = signal_file.as_ref().map(|f| f.path().to_string_lossy().to_string());
            exec(command, no_exit, signal_file_path)?;
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
    signal_file: Option<NamedTempFile>,
) -> Result<()> {
    let result = do_drive_child(master, input_rx, output_tx).await;
    eprintln!("sending HUP signal to the child process");
    unsafe { libc::kill(child.as_raw(), libc::SIGHUP) };
    eprintln!("waiting for the child process to exit");

    // Signal the waitexit process by deleting the signal file
    if let Some(signal_file) = signal_file {
        eprintln!("deleting signal file to signal waitexit");
        drop(signal_file); // This automatically deletes the temp file
    }

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

    result
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

fn exec(command: String, no_exit: bool, signal_file_path: Option<String>) -> io::Result<()> {
    let final_command = if let (true, Some(signal_file)) = (no_exit, signal_file_path) {
        let ht_binary = env::current_exe()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?
            .to_string_lossy()
            .to_string();
        format!("{} ; while [ -f '{}' ]; do sleep 0.1; done", command, signal_file)
    } else {
        command
    };

    let command = ["/bin/sh".to_owned(), "-c".to_owned(), final_command]
        .iter()
        .map(|s| CString::new(s.as_bytes()))
        .collect::<Result<Vec<CString>, NulError>>()?;

    env::set_var("TERM", "xterm-256color");
    unsafe { signal::signal(Signal::SIGPIPE, SigHandler::SigDfl) }?;
    unistd::execvp(&command[0], &command)?;
    unsafe { libc::_exit(1) }
}
