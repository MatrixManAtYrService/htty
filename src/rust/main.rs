//  Main entry point for the ht binary
// Test comment for build optimization verification

mod api;
mod cli;
mod command;
mod locale;
mod nbio;
mod pty;
mod session;
use anyhow::{Context, Result};
use command::Command;
use nix::libc;
use session::Session;
use std::io::{BufRead, Write};
use std::net::{SocketAddr, TcpListener};
use std::path::PathBuf;
use tokio::{sync::mpsc, task::JoinHandle};

#[tokio::main]
async fn main() -> Result<()> {
    locale::check_utf8_locale()?;
    let cli = cli::Cli::new()?;

    // Handle waitexit subcommand
    if let Some(cli::Commands::WaitExit { signal_file }) = &cli.command {
        return handle_waitexit(signal_file.clone()).await;
    }

    let (input_tx, input_rx) = mpsc::channel(1024);
    let (output_tx, output_rx) = mpsc::channel(1024);
    let (command_tx, command_rx) = mpsc::channel(1024);
    let (clients_tx, clients_rx) = mpsc::channel(1);
    let (pid_tx, pid_rx) = mpsc::channel(1);
    let (exit_code_tx, exit_code_rx) = mpsc::channel(1);

    start_http_api(cli.listen, clients_tx.clone()).await?;
    let api = start_stdio_api(command_tx.clone(), clients_tx, cli.subscribe.unwrap_or_default());
    let pty = start_pty(cli.shell_command.clone(), &cli.size, input_rx, output_tx, pid_tx, exit_code_tx, command_tx.clone())?;
    let session = build_session(&cli.size);
    run_event_loop(output_rx, input_tx, command_rx, clients_rx, pid_rx, exit_code_rx, session, api, &cli).await?;
    pty.await?
}

async fn handle_waitexit(signal_file: PathBuf) -> Result<()> {
    // Create the FIFO (step 3 in desired flow)
    let fifo_path_str = signal_file.to_string_lossy();
    let fifo_path_cstr = std::ffi::CString::new(fifo_path_str.as_bytes()).unwrap();
    
    unsafe {
        let result = libc::mkfifo(fifo_path_cstr.as_ptr(), 0o600);
        if result != 0 {
            return Ok(());
        }
    }
    
    // Block reading from FIFO - this signals to parent that command completed (step 4-5)
    // Parent will detect FIFO existence and know command is done
    if let Ok(file) = std::fs::File::open(&signal_file) {
        let reader = std::io::BufReader::new(file);
        for line in reader.lines() {
            if let Ok(line) = line {
                if line.trim() == "exit" {
                    break;
                }
            }
        }
    }
    
    Ok(())
}

fn build_session(size: &cli::Size) -> Session {
    Session::new(size.cols(), size.rows())
}

fn start_stdio_api(
    command_tx: mpsc::Sender<Command>,
    clients_tx: mpsc::Sender<session::Client>,
    sub: api::Subscription,
) -> JoinHandle<Result<()>> {
    tokio::spawn(api::stdio::start(command_tx, clients_tx, sub))
}

fn start_pty(
    command: Vec<String>,
    size: &cli::Size,
    input_rx: mpsc::Receiver<Vec<u8>>,
    output_tx: mpsc::Sender<Vec<u8>>,
    pid_tx: mpsc::Sender<i32>,
    exit_code_tx: mpsc::Sender<i32>,
    command_tx: mpsc::Sender<Command>,
) -> Result<JoinHandle<Result<()>>> {
    let command = command.join(" ");
    eprintln!("launching \"{}\" in terminal of size {}", command, size);

    Ok(tokio::spawn(pty::spawn(
        command, size, input_rx, output_tx, pid_tx, exit_code_tx, command_tx,
    )?))
}

async fn start_http_api(
    listen_addr: Option<SocketAddr>,
    clients_tx: mpsc::Sender<session::Client>,
) -> Result<()> {
    if let Some(addr) = listen_addr {
        let listener = TcpListener::bind(addr).context("cannot start HTTP listener")?;
        tokio::spawn(api::http::start(listener, clients_tx).await?);
    }

    Ok(())
}

async fn run_event_loop(
    mut output_rx: mpsc::Receiver<Vec<u8>>,
    input_tx: mpsc::Sender<Vec<u8>>,
    mut command_rx: mpsc::Receiver<Command>,
    mut clients_rx: mpsc::Receiver<session::Client>,
    mut pid_rx: mpsc::Receiver<i32>,
    mut exit_code_rx: mpsc::Receiver<i32>,
    mut session: Session,
    mut api_handle: JoinHandle<Result<()>>,
    _cli: &cli::Cli,
) -> Result<()> {
    let mut serving = true;
    let mut last_command_time = std::time::Instant::now();
    let mut pending_waitexit: Option<std::path::PathBuf> = None;

    // Timer for checking command channel emptiness
    let mut emptiness_check_interval = tokio::time::interval(std::time::Duration::from_millis(10));

    loop {
        tokio::select! {
            result = output_rx.recv() => {
                match result {
                    Some(data) => {
                        session.output(String::from_utf8_lossy(&data).to_string());
                    },

                    None => {
                        eprintln!("Process exited, shutting down...");
                        break;
                    }
                }
            }

            pid = pid_rx.recv() => {
                if let Some(pid) = pid {
                    session.emit_pid(pid);
                }
            }

            exit_code = exit_code_rx.recv() => {
                if let Some(exit_code) = exit_code {
                    session.emit_exit_code(exit_code);
                }
            }

            _ = emptiness_check_interval.tick() => {
                // Check if we should signal waitexit due to channel emptiness
                if let Some(fifo_path) = &pending_waitexit {
                    let emptiness_duration = last_command_time.elapsed();
                    if emptiness_duration >= std::time::Duration::from_millis(200) {
                        // Channel has been empty for 200ms, signal waitexit
                        session.emit_debug_event("signalingWaitexit");
                        
                        if fifo_path.exists() {
                            if let Ok(mut file) = std::fs::OpenOptions::new()
                                .write(true)
                                .open(fifo_path) 
                            {
                                use std::io::Write;
                                let _ = writeln!(file, "exit");
                                let _ = file.flush();
                                session.emit_debug_event("exitSignalSent");
                            } else {
                                session.emit_debug_event("exitSignalFailed");
                            }
                        } else {
                            session.emit_debug_event("fifoMissingForExit");
                        }
                        
                        pending_waitexit = None; // Clear pending state
                    }
                }
            }

            command = command_rx.recv() => {
                // Update last command time whenever we receive any command
                last_command_time = std::time::Instant::now();
                
                match command {
                    Some(Command::Input(seqs)) => {
                        let data = command::seqs_to_bytes(&seqs, session.cursor_key_app_mode());
                        input_tx.send(data).await?;
                    }

                    Some(Command::Snapshot) => {
                        session.snapshot();
                    }

                    Some(Command::Resize(cols, rows)) => {
                        session.resize(cols, rows);
                    }

                    Some(Command::Debug(message)) => {
                        // Emit all debug messages as debug events
                        session.emit_debug_event(&message);
                    }

                    Some(Command::CommandCompleted(fifo_path)) => {
                        session.emit_command_completed();
                        // Set up pending waitexit - it will be triggered when channel is empty for 200ms
                        pending_waitexit = Some(fifo_path);
                        session.emit_debug_event("commandCompletedReceived");
                    }

                    Some(Command::SignalWaitexit(fifo_path)) => {
                        // This is the old direct signaling - we'll keep it for now but it shouldn't be used
                        session.emit_debug_event("signalingWaitexit");
                        
                        // Write "exit" to FIFO to signal waitexit to complete
                        if fifo_path.exists() {
                            if let Ok(mut file) = std::fs::OpenOptions::new()
                                .write(true)
                                .open(&fifo_path) 
                            {
                                use std::io::Write;
                                let _ = writeln!(file, "exit");
                                let _ = file.flush();
                                session.emit_debug_event("exitSignalSent");
                            } else {
                                session.emit_debug_event("exitSignalFailed");
                            }
                        } else {
                            session.emit_debug_event("fifoMissingForExit");
                        }
                    }

                    Some(Command::Exit) => {
                        eprintln!("Exit command received, signaling waitexit and shutting down...");
                        // Send a special debug event to signal that exit was requested
                        session.emit_debug_event("exitRequested");
                        break;
                    }

                    None => {
                        eprintln!("stdin closed, shutting down...");
                        break;
                    }
                }
            }

            client = clients_rx.recv(), if serving => {
                match client {
                    Some(client) => {
                        client.accept(session.subscribe());
                    }

                    None => {
                        serving = false;
                    }
                }
            }

            _ = &mut api_handle => {
                eprintln!("API handle closed, shutting down...");
                break;
            }
        }
    }

    Ok(())
}
