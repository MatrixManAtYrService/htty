/*!
Python bindings for htty using PyO3.

This module provides Python classes and functions for interacting with the ht binary
as a subprocess, leveraging the --start-on-output and exit commands for reliable operation.
*/

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio, Child};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use serde_json::{json, Value};
use which::which;
use nix::libc;

/// Python wrapper for special key constants
#[pyclass]
#[derive(Clone)]
pub struct Press;

#[pymethods]
impl Press {
    #[classattr]
    fn ENTER() -> &'static str { "Enter" }
    
    #[classattr]
    fn TAB() -> &'static str { "Tab" }
    
    #[classattr]
    fn BACKSPACE() -> &'static str { "Backspace" }
    
    #[classattr]
    fn ESCAPE() -> &'static str { "Escape" }
    
    #[classattr]
    fn SPACE() -> &'static str { "Space" }
    
    #[classattr]
    fn UP() -> &'static str { "Up" }
    
    #[classattr]
    fn DOWN() -> &'static str { "Down" }
    
    #[classattr]
    fn LEFT() -> &'static str { "Left" }
    
    #[classattr]
    fn RIGHT() -> &'static str { "Right" }
    
    #[classattr]
    fn CTRL_C() -> &'static str { "C-c" }
    
    #[classattr]
    fn CTRL_D() -> &'static str { "C-d" }
}

/// Result from taking a terminal snapshot
#[pyclass]
#[derive(Clone)]
pub struct PySnapshotResult {
    #[pyo3(get)]
    pub text: String,
    
    #[pyo3(get)]
    pub html: String,
    
    #[pyo3(get)]
    pub raw_seq: String,
}

#[pymethods]
impl PySnapshotResult {
    #[new]
    fn new(text: String, html: String, raw_seq: String) -> Self {
        Self { text, html, raw_seq }
    }
    
    fn __repr__(&self) -> String {
        format!("SnapshotResult(text={:?}, html=<{} chars>, raw_seq=<{} chars>)", 
                self.text, self.html.len(), self.raw_seq.len())
    }
}

/// Simple session for in-memory terminal simulation
#[pyclass]
pub struct PySession {
    rows: usize,
    cols: usize,
    session: crate::session::Session,
}

#[pymethods]
impl PySession {
    #[new]
    fn new(rows: usize, cols: usize) -> Self {
        Self {
            rows,
            cols,
            session: crate::session::Session::new(cols, rows),
        }
    }
    
    fn send_input(&mut self, keys: Vec<String>) -> PyResult<()> {
        // Since the Session doesn't expose send_input publicly and we're doing subprocess approach anyway,
        // this is just a placeholder for the PySession wrapper
        // In practice, use HTProcess for real terminal interaction
        Ok(())
    }
    
    fn snapshot(&mut self) -> PyResult<PySnapshotResult> {
        // This is a simplified version for the Session wrapper
        // In practice, you'd use the HTProcess for real snapshots
        Ok(PySnapshotResult::new(
            "Mock session output".to_string(),
            "<pre>Mock session output</pre>".to_string(),
            "Mock session output".to_string(),
        ))
    }
    
    fn resize(&mut self, cols: usize, rows: usize) -> PyResult<()> {
        self.cols = cols;
        self.rows = rows;
        // Note: Real session resize would require calling session.resize() 
        // but the current Session API doesn't expose this publicly
        Ok(())
    }
}

/// Controller for subprocess lifecycle management
#[pyclass]
pub struct PySubprocessController {
    pid: Option<i32>,
    exit_code: Option<i32>,
}

#[pymethods]
impl PySubprocessController {
    #[new]
    fn new(pid: Option<i32>) -> Self {
        Self { pid, exit_code: None }
    }
    
    fn terminate(&mut self) -> PyResult<()> {
        if let Some(pid) = self.pid {
            unsafe {
                libc::kill(pid, libc::SIGTERM);
            }
        }
        Ok(())
    }
    
    fn kill(&mut self) -> PyResult<()> {
        if let Some(pid) = self.pid {
            unsafe {
                libc::kill(pid, libc::SIGKILL);
            }
        }
        Ok(())
    }
    
    fn wait(&mut self, timeout: Option<f64>) -> PyResult<()> {
        // This is a simple wait implementation
        // In a real implementation, you'd want to wait for the process to finish
        let timeout_duration = Duration::from_secs_f64(timeout.unwrap_or(30.0));
        let start = std::time::Instant::now();
        
        // For now, just sleep a bit to simulate waiting
        // In the full implementation, this would actually monitor the process
        while start.elapsed() < timeout_duration {
            std::thread::sleep(Duration::from_millis(100));
            // In a real implementation, check if process is still running
            // For now, just return after a short wait
            if start.elapsed() > Duration::from_millis(500) {
                break;
            }
        }
        Ok(())
    }
    
    #[getter]
    fn pid(&self) -> Option<i32> {
        self.pid
    }
    
    #[getter]
    fn exit_code(&self) -> Option<i32> {
        self.exit_code
    }
}

/// Main process management for subprocess approach
#[pyclass]
pub struct PyHTProcess {
    child: Arc<Mutex<Option<Child>>>,
    events: Arc<Mutex<Vec<Value>>>,
    subprocess_controller: PySubprocessController,
    exited: bool,
}

#[pymethods]
impl PyHTProcess {
    fn send_keys(&mut self, keys: &Bound<'_, PyAny>) -> PyResult<()> {
        // Handle both single strings and lists of strings
        let key_list: Vec<String> = if let Ok(key_str) = keys.extract::<String>() {
            vec![key_str]
        } else if let Ok(key_vec) = keys.extract::<Vec<String>>() {
            key_vec
        } else {
            return Err(pyo3::exceptions::PyTypeError::new_err("keys must be a string or list of strings"));
        };
        
        let message = json!({
            "type": "sendKeys",
            "keys": key_list
        });
        
        self.send_json_message(message)
    }
    
    fn snapshot(&mut self, delay: Option<u64>) -> PyResult<PySnapshotResult> {
        let message = if let Some(delay_ms) = delay {
            json!({
                "type": "takeSnapshot",
                "delay": delay_ms
            })
        } else {
            json!({
                "type": "takeSnapshot"
            })
        };
        
        self.send_json_message(message)?;
        
        // Wait for snapshot event in the events
        let timeout = std::time::Instant::now() + Duration::from_secs(5);
        
        while std::time::Instant::now() < timeout {
            let events = self.events.lock().unwrap();
            for event in events.iter().rev() {
                if event.get("type") == Some(&Value::String("snapshot".to_string())) {
                    if let Some(data) = event.get("data") {
                        let text = data.get("text")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        let seq = data.get("seq")
                            .and_then(|v| v.as_str())
                            .unwrap_or("")
                            .to_string();
                        
                        // Simple HTML conversion (just escape and wrap in <pre>)
                        let html = format!("<pre>{}</pre>", html_escape::encode_text(&text));
                        
                        return Ok(PySnapshotResult::new(text, html, seq));
                    }
                }
            }
            drop(events);
            
            std::thread::sleep(Duration::from_millis(100));
        }
        
        Err(pyo3::exceptions::PyTimeoutError::new_err("Snapshot timeout"))
    }
    
    fn exit(&mut self, timeout: Option<f64>) -> PyResult<i32> {
        // Send exit command
        let message = json!({"type": "exit"});
        self.send_json_message(message)?;
        
        // Wait for process to exit
        let timeout_duration = Duration::from_secs_f64(timeout.unwrap_or(5.0));
        let start = std::time::Instant::now();
        
        loop {
            {
                let mut child_guard = self.child.lock().unwrap();
                if let Some(ref mut child) = child_guard.as_mut() {
                    match child.try_wait() {
                        Ok(Some(exit_status)) => {
                            self.exited = true;
                            let code = exit_status.code().unwrap_or(-1);
                            self.subprocess_controller.exit_code = Some(code);
                            return Ok(code);
                        }
                        Ok(None) => {
                            // Still running, check timeout
                            if start.elapsed() > timeout_duration {
                                child.kill().ok();
                                return Err(pyo3::exceptions::PyTimeoutError::new_err("Exit timeout"));
                            }
                        }
                        Err(e) => {
                            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!("Wait error: {}", e)));
                        }
                    }
                }
            }
            
            std::thread::sleep(Duration::from_millis(100));
        }
    }
    
    #[getter]
    fn subprocess_controller(&self) -> PySubprocessController {
        PySubprocessController::new(self.subprocess_controller.pid)
    }
    
    #[getter]
    fn exited(&self) -> bool {
        self.exited
    }
}

impl PyHTProcess {
    fn send_json_message(&mut self, message: Value) -> PyResult<()> {
        let mut child_guard = self.child.lock().unwrap();
        if let Some(ref mut child) = child_guard.as_mut() {
            if let Some(ref mut stdin) = child.stdin.as_mut() {
                let json_str = serde_json::to_string(&message)
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("JSON error: {}", e)))?;
                
                writeln!(stdin, "{}", json_str)
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Write error: {}", e)))?;
                
                stdin.flush()
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Flush error: {}", e)))?;
            }
        }
        Ok(())
    }
}

/// Find the ht binary to use
fn find_ht_binary() -> PyResult<String> {
    // Try to find the ht binary that we built
    if let Ok(current_exe) = std::env::current_exe() {
        let parent_dir = current_exe.parent();
        if let Some(parent) = parent_dir {
            let ht_path = parent.join("ht");
            if ht_path.exists() {
                return Ok(ht_path.to_string_lossy().to_string());
            }
        }
    }
    
    // Fall back to system PATH
    which("ht")
        .map(|path| path.to_string_lossy().to_string())
        .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("ht binary not found in PATH"))
}

/// Run a command using ht subprocess approach
#[pyfunction]
pub fn run(
    command: &Bound<'_, PyAny>,
    rows: Option<usize>,
    cols: Option<usize>,
    no_exit: Option<bool>,
    start_on_output: Option<bool>,
) -> PyResult<PyHTProcess> {
    let ht_binary = find_ht_binary()?;
    
    // Handle both string commands and pre-split argument lists
    let cmd_args: Vec<String> = if let Ok(cmd_str) = command.extract::<String>() {
        // Split string into arguments using shell-like parsing
        shell_words::split(&cmd_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid command string: {}", e)))?
    } else if let Ok(cmd_vec) = command.extract::<Vec<String>>() {
        cmd_vec
    } else {
        return Err(pyo3::exceptions::PyTypeError::new_err("command must be a string or list of strings"));
    };
    
    let mut cmd = Command::new(&ht_binary);
    
    // Add subscription for events we need
    cmd.args(&["--subscribe", "init,snapshot,output,resize,pid,exitCode"]);
    
    // Add size if specified
    if let (Some(r), Some(c)) = (rows, cols) {
        cmd.args(&["--size", &format!("{}x{}", c, r)]);
    }
    
    // Add flags
    if no_exit.unwrap_or(true) {
        cmd.arg("--no-exit");
    }
    
    if start_on_output.unwrap_or(true) {
        cmd.arg("--start-on-output");
    }
    
    // Add the command to run
    cmd.arg("--");
    cmd.args(&cmd_args);
    
    // Configure stdio
    cmd.stdin(Stdio::piped())
       .stdout(Stdio::piped())
       .stderr(Stdio::piped());
    
    // Start the process
    let child = cmd.spawn()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to start ht: {}", e)))?;
    
    let events = Arc::new(Mutex::new(Vec::new()));
    let child_arc = Arc::new(Mutex::new(Some(child)));
    
    // Start reader thread for stdout
    if let Some(stdout) = child_arc.lock().unwrap().as_mut().unwrap().stdout.take() {
        let events_clone = events.clone();
        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                if let Ok(line) = line {
                    if let Ok(event) = serde_json::from_str::<Value>(&line) {
                        events_clone.lock().unwrap().push(event);
                    }
                }
            }
        });
    }
    
    // Wait a bit for initial events
    std::thread::sleep(Duration::from_millis(500));
    
    // Try to get PID from events
    let mut subprocess_pid = None;
    {
        let events_guard = events.lock().unwrap();
        for event in events_guard.iter() {
            if event.get("type") == Some(&Value::String("pid".to_string())) {
                if let Some(data) = event.get("data") {
                    if let Some(pid_val) = data.get("pid") {
                        if let Some(pid) = pid_val.as_i64() {
                            subprocess_pid = Some(pid as i32);
                            break;
                        }
                    }
                }
            }
        }
    }
    
    Ok(PyHTProcess {
        child: child_arc,
        events,
        subprocess_controller: PySubprocessController::new(subprocess_pid),
        exited: false,
    })
}

/// Register all Python classes and functions
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Press>()?;
    m.add_class::<PySnapshotResult>()?;
    m.add_class::<PySession>()?;
    m.add_class::<PySubprocessController>()?;
    m.add_class::<PyHTProcess>()?;
    m.add_function(wrap_pyfunction!(run, m)?)?;
    
    // Add version info
    m.add("__version__", "0.3.0")?;
    
    Ok(())
}
