/*! 
# htty - Headless Terminal

A library and binary for headless terminal emulation.

This is a fork of ht with additional features. Python integration is provided
through the `htty` Python package which calls the `ht` binary as a subprocess.

## Usage as a library

```rust
use htty::{Command, Session, InputSeq};

let mut session = Session::new(80, 24);
// Simulate terminal output
session.output("hello\n".to_string());
// Take a snapshot of the current terminal state
session.snapshot();

// Create input commands (these would be sent through the command system)
let _input_command = Command::Input(vec![InputSeq::Standard("hello".to_string())]);
```

## Python integration

Python integration is provided by the `htty` Python package, which calls the
`ht` binary as a subprocess for reliable terminal automation.
*/

// Re-export the main modules
pub mod api;
pub mod cli;
pub mod command;
pub mod locale;
pub mod nbio;
pub mod pty;
pub mod session;

// Re-export key types for library users
pub use command::{Command, InputSeq};
pub use session::{Event, Session};
