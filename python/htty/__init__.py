"""
htty - Headless Terminal Python Library

A Python library for terminal automation, providing both synchronous CLI tools
and asynchronous library access for subprocess interaction.

This is a fork of ht with enhanced Python integration and reliable subprocess management.
"""

from contextlib import contextmanager
from typing import List, Union, Optional

# Import the core Rust implementation  
from ._htty import (
    PyHTProcess as HTProcess,
    PySession as Session,
    PySnapshotResult as SnapshotResult,
    PySubprocessController as SubprocessController,
    Press,
    run,
)

__all__ = [
    "HTProcess",
    "Session", 
    "SnapshotResult",
    "SubprocessController", 
    "Press",
    "run",
    "ht_process",
]

__version__ = "0.3.0"


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
    # Handle both string commands and pre-split argument lists
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command
        
    proc = run(cmd_args, rows=rows, cols=cols, no_exit=no_exit, start_on_output=start_on_output)
    try:
        yield proc
    finally:
        try:
            # Try to exit cleanly
            proc.exit(timeout=5.0)
        except Exception:
            # If clean exit fails, force terminate
            try:
                proc.subprocess_controller.terminate()
            except Exception:
                pass
