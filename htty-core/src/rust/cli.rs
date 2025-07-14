use crate::api::Subscription;
use anyhow::{bail, Result};
use nix::pty;
use std::{fmt::Display, net::SocketAddr, ops::Deref, str::FromStr, path::PathBuf, env};

#[derive(Debug)]
pub struct Cli {
    pub command: Option<Commands>,
    pub size: Size,
    pub shell_command: Vec<String>,
    pub listen: Option<SocketAddr>,
    pub subscribe: Option<Subscription>,
}

#[derive(Debug)]
pub enum Commands {
    WaitExit {
        signal_file: PathBuf,
    },
}

impl Cli {
    pub fn new() -> Result<Self> {
        let args: Vec<String> = env::args().collect();
        parse_args(&args)
    }
}

fn parse_args(args: &[String]) -> Result<Cli> {
    let mut cli = Cli {
        command: None,
        size: Size::default(),
        shell_command: vec!["bash".to_string()],
        listen: None,
        subscribe: None,
    };

    let mut i = 1; // Skip program name
    
    while i < args.len() {
        match args[i].as_str() {
            "--help" | "-h" => {
                print_help(&args[0]);
                std::process::exit(0);
            }
            "--version" | "-V" => {
                // [[[cog
                // import os
                // cog.out(f'println!("{os.environ["HTTY_VERSION_INFO_HT"]}");')
                // ]]]
                println!("ht 0.2.12 (unknown)");
                // [[[end]]]
                std::process::exit(0);
            }
            "--size" => {
                if i + 1 >= args.len() {
                    bail!("--size requires a value");
                }
                i += 1;
                cli.size = args[i].parse()?;
            }
            "--listen" | "-l" => {
                // Handle optional value
                if i + 1 < args.len() && !args[i + 1].starts_with('-') {
                    i += 1;
                    cli.listen = Some(args[i].parse()?);
                } else {
                    cli.listen = Some("127.0.0.1:0".parse()?);
                }
            }
            "--subscribe" => {
                if i + 1 >= args.len() {
                    bail!("--subscribe requires a value");
                }
                i += 1;
                cli.subscribe = Some(args[i].parse().map_err(|e: String| anyhow::anyhow!(e))?);
            }
            "wait-exit" => {
                if i + 1 >= args.len() {
                    bail!("wait-exit requires a signal file path");
                }
                i += 1;
                cli.command = Some(Commands::WaitExit {
                    signal_file: PathBuf::from(&args[i]),
                });
                break; // No more parsing after subcommand
            }
            "--" => {
                // Everything after -- is the shell command
                i += 1;
                if i < args.len() {
                    cli.shell_command = args[i..].to_vec();
                }
                break;
            }
            arg if arg.starts_with('-') => {
                bail!("Unknown option: {}", arg);
            }
            _ => {
                // Positional arguments are shell command
                cli.shell_command = args[i..].to_vec();
                break;
            }
        }
        i += 1;
    }

    Ok(cli)
}

fn print_help(program_name: &str) {
    println!("Usage: {} [OPTIONS] [SHELL_COMMAND]... [COMMAND]", program_name);
    println!();
    println!("Commands:");
    println!("  wait-exit  Wait for a signal file to be deleted before exiting");
    println!("  help       Print this message or the help of the given subcommand(s)");
    println!();
    println!("Arguments:");
    println!("  [SHELL_COMMAND]...  Command to run inside the terminal [default: bash]");
    println!();
    println!("Options:");
    println!("      --size <COLSxROWS>        Terminal size [default: 120x40]");
    println!("  -l, --listen [<LISTEN_ADDR>]  Enable HTTP server");
    println!("      --subscribe <EVENTS>      Subscribe to events");
    println!("  -h, --help                    Print help");
    println!("  -V, --version                 Print version");
}

#[derive(Debug, Clone)]
pub struct Size(pty::Winsize);

impl Size {
    pub fn cols(&self) -> usize {
        self.0.ws_col as usize
    }

    pub fn rows(&self) -> usize {
        self.0.ws_row as usize
    }
}

impl Default for Size {
    fn default() -> Self {
        Size(pty::Winsize {
            ws_col: 120,
            ws_row: 40,
            ws_xpixel: 0,
            ws_ypixel: 0,
        })
    }
}

impl FromStr for Size {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.split_once('x') {
            Some((cols, rows)) => {
                let cols: u16 = cols.parse()?;
                let rows: u16 = rows.parse()?;

                let winsize = pty::Winsize {
                    ws_col: cols,
                    ws_row: rows,
                    ws_xpixel: 0,
                    ws_ypixel: 0,
                };

                Ok(Size(winsize))
            }

            None => {
                bail!("invalid size format: {s}");
            }
        }
    }
}

impl Deref for Size {
    type Target = pty::Winsize;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl Display for Size {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}x{}", self.0.ws_col, self.0.ws_row)
    }
}
