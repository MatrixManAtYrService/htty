/*! 
# htty - Headless Terminal

A library and binary for headless terminal emulation, with Python bindings.

This is a fork of ht with additional features and Python integration.

## Usage as a library

```rust
use htty::{Command, Session, InputSeq};

let mut session = Session::new(80, 24);
session.send_input(vec![InputSeq::Text("hello".to_string())]);
let snapshot = session.snapshot();
```

## Python integration

When compiled with the `python` feature, this crate provides Python bindings
via PyO3 that allow subprocess control and terminal interaction.
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

// Python bindings (only available with python feature)
#[cfg(feature = "python")]
pub mod python;

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Python module initialization
#[cfg(feature = "python")]
#[pymodule]
fn _htty(m: &Bound<'_, PyModule>) -> PyResult<()> {
    python::register_module(m)
}
