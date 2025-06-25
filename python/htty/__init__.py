"""
htty - Headless Terminal Python Library

A Python library for terminal automation, providing both synchronous CLI tools
and asynchronous library access for subprocess interaction.

This is a fork of ht with enhanced Python integration and reliable subprocess management.
"""

import json
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import List, Union, Optional, Dict, Any
import os

from ._find_ht import find_ht_bin

__all__ = [
    "HTProcess",
    "SnapshotResult", 
    "Press",
    "run",
    "ht_process",
    "find_ht_bin",
]

__version__ = "0.3.0"


class Press:
    """Key constants for terminal input"""
    ENTER = "Enter"
    TAB = "Tab"
    BACKSPACE = "Backspace"
    ESCAPE = "Escape"
    SPACE = "Space"
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"
    CTRL_C = "C-c"
    CTRL_D = "C-d"


class SnapshotResult:
    """Result from taking a terminal snapshot"""
    
    def __init__(self, text: str, html: str, raw_seq: str):
        self.text = text
        self.html = html
        self.raw_seq = raw_seq
    
    def __repr__(self) -> str:
        return f"SnapshotResult(text={self.text!r}, html=<{len(self.html)} chars>, raw_seq=<{len(self.raw_seq)} chars>)"


class HTProcess:
    """Main process management for subprocess approach"""
    
    def __init__(self, process: subprocess.Popen, events: List[Dict[str, Any]]):
        self.process = process
        self.events = events
        self.events_lock = threading.Lock()
        self.exited = False
        
        # Start reader thread
        self._start_reader_thread()
    
    def _start_reader_thread(self):
        """Start thread to read events from ht process stdout"""
        def reader():
            if self.process.stdout:
                for line in iter(self.process.stdout.readline, b''):
                    try:
                        event = json.loads(line.decode('utf-8').strip())
                        with self.events_lock:
                            self.events.append(event)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Skip non-JSON lines
                        pass
        
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
    
    def send_keys(self, keys: Union[str, List[str]]) -> None:
        """Send keys to the terminal"""
        if isinstance(keys, str):
            key_list = [keys]
        else:
            key_list = keys
            
        message = json.dumps({
            "type": "sendKeys",
            "keys": key_list
        })
        
        if self.process.stdin:
            self.process.stdin.write((message + "\n").encode('utf-8'))
            self.process.stdin.flush()
    
    def snapshot(self, timeout: float = 5.0) -> SnapshotResult:
        """Take a snapshot of the terminal"""
        # Send snapshot request
        message = json.dumps({"type": "takeSnapshot"})
        
        if self.process.stdin:
            self.process.stdin.write((message + "\n").encode('utf-8'))
            self.process.stdin.flush()
        
        # Wait for snapshot event
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.events_lock:
                # Look for most recent snapshot event
                for event in reversed(self.events):
                    if event.get("type") == "snapshot":
                        if "data" in event:
                            data = event["data"]
                            text = data.get("text", "")
                            seq = data.get("seq", "")
                            # Simple HTML conversion
                            html = f"<pre>{text}</pre>"
                            return SnapshotResult(text, html, seq)
            
            time.sleep(0.1)
        
        raise TimeoutError("Snapshot timeout")
    
    def exit(self, timeout: float = 5.0) -> int:
        """Exit the ht process"""
        if self.exited:
            return self.process.returncode or 0
            
        # Send exit command
        message = json.dumps({"type": "exit"})
        
        if self.process.stdin:
            self.process.stdin.write((message + "\n").encode('utf-8'))
            self.process.stdin.flush()
        
        # Wait for process to exit
        try:
            returncode = self.process.wait(timeout=timeout)
            self.exited = True
            return returncode
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't exit cleanly
            self.process.kill()
            self.process.wait()
            self.exited = True
            raise TimeoutError("Exit timeout")


def run(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
    start_on_output: bool = True,
) -> HTProcess:
    """
    Run a command using ht subprocess approach
    
    Args:
        command: The command to run (string or list of strings)
        rows: Number of rows for the terminal size
        cols: Number of columns for the terminal size
        no_exit: Whether to use --no-exit flag (default: True)
        start_on_output: Whether to use --start-on-output flag (default: True)
        
    Returns:
        HTProcess instance for controlling the subprocess
    """
    ht_binary = find_ht_bin()
    
    # Handle both string commands and pre-split argument lists
    if isinstance(command, str):
        # Simple split for now - could use shlex for more robust parsing
        cmd_args = command.split()
    else:
        cmd_args = command
    
    # Build ht command
    ht_cmd = [ht_binary]
    
    # Add subscription for events we need
    ht_cmd.extend(["--subscribe", "init,snapshot,output,resize,pid,exitCode"])
    
    # Add size if specified
    if rows is not None and cols is not None:
        ht_cmd.extend(["--size", f"{cols}x{rows}"])
    
    # Add flags
    if no_exit:
        ht_cmd.append("--no-exit")
    
    if start_on_output:
        ht_cmd.append("--start-on-output")
    
    # Add the command to run
    ht_cmd.append("--")
    ht_cmd.extend(cmd_args)
    
    # Start the process
    process = subprocess.Popen(
        ht_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False  # We handle encoding ourselves
    )
    
    events = []
    return HTProcess(process, events)


@contextmanager
def ht_process(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None, 
    no_exit: bool = True,
    start_on_output: bool = True,
):
    """
    Context manager for HTProcess that ensures proper cleanup.
    
    Usage:
        with ht_process("vim", rows=20, cols=50) as proc:
            proc.send_keys([Press.ENTER])
            snapshot = proc.snapshot()
            # Process is automatically cleaned up when exiting the context
            
    Args:
        command: The command to run (string or list of strings)
        rows: Number of rows for the terminal size
        cols: Number of columns for the terminal size
        no_exit: Whether to use --no-exit flag (default: True)
        start_on_output: Whether to use --start-on-output flag (default: True)
        
    Yields:
        HTProcess instance with automatic cleanup
    """
    proc = run(command, rows=rows, cols=cols, no_exit=no_exit, start_on_output=start_on_output)
    try:
        yield proc
    finally:
        try:
            # Try to exit cleanly
            proc.exit(timeout=5.0)
        except Exception:
            # If clean exit fails, force terminate
            try:
                proc.process.terminate()
                proc.process.wait(timeout=2.0)
            except Exception:
                proc.process.kill()
                proc.process.wait()
