"""
Core classes for htty terminal process management.
"""

import json
import logging
import os
import queue
import signal
import subprocess
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

from .html_utils import simple_ansi_to_html
from .keys import KeyInput, keys_to_strings
from ._find_ht import find_ht_bin

__all__ = [
    "SnapshotResult", 
    "SubprocessController", 
    "HTProcess", 
    "run", 
    "ht_process",
    "DEFAULT_SLEEP_AFTER_KEYS",
    "DEFAULT_SUBPROCESS_WAIT_TIMEOUT",
    "DEFAULT_SNAPSHOT_TIMEOUT",
    "DEFAULT_EXIT_TIMEOUT",
    "DEFAULT_GRACEFUL_TERMINATION_TIMEOUT",
    "SNAPSHOT_RETRY_TIMEOUT",
    "SUBPROCESS_EXIT_DETECTION_DELAY",
    "MAX_SNAPSHOT_RETRIES",
]

# Constants
DEFAULT_SLEEP_AFTER_KEYS = 0.1
DEFAULT_SUBPROCESS_WAIT_TIMEOUT = 2.0
DEFAULT_SNAPSHOT_TIMEOUT = 5.0
DEFAULT_EXIT_TIMEOUT = 5.0
DEFAULT_GRACEFUL_TERMINATION_TIMEOUT = 5.0
SNAPSHOT_RETRY_TIMEOUT = 0.5
SUBPROCESS_EXIT_DETECTION_DELAY = 0.2
MAX_SNAPSHOT_RETRIES = 10


class SnapshotResult:
    """Result of taking a terminal snapshot"""
    
    def __init__(self, text: str, html: str, raw_seq: str):
        self.text = text
        self.html = html
        self.raw_seq = raw_seq
    
    def __repr__(self):
        return f"SnapshotResult(text={self.text!r}, html=<{len(self.html)} chars>, raw_seq=<{len(self.raw_seq)} chars>)"


class SubprocessController:
    """Controller for the subprocess being monitored by ht."""

    def __init__(self, pid: Optional[int] = None):
        self.pid = pid
        self.exit_code: Optional[int] = None
        self._termination_initiated = False

    def poll(self) -> Optional[int]:
        """Check if the subprocess is still running."""
        if self.pid is None:
            return self.exit_code
        try:
            os.kill(self.pid, 0)
            return None  # Process is still running
        except OSError:
            return self.exit_code  # Process has exited

    def terminate(self) -> None:
        """Terminate the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
            self._termination_initiated = True
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            pass  # Process may have already exited

    def kill(self) -> None:
        """Force kill the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
            self._termination_initiated = True
            os.kill(self.pid, signal.SIGKILL)
        except OSError:
            pass  # Process may have already exited

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """
        Wait for the subprocess to finish.
        
        Args:
            timeout: Maximum time to wait (in seconds). If None, waits indefinitely.
            
        Returns:
            The exit code of the subprocess, or None if timeout reached
        """
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")

        start_time = time.time()
        while True:
            try:
                os.kill(self.pid, 0)  # Check if process is still running
                
                # Check timeout
                if timeout is not None and (time.time() - start_time) > timeout:
                    return None  # Timeout reached
                    
                time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
            except OSError:
                # Process has exited
                # Try to get the actual exit code
                try:
                    pid_result, status = os.waitpid(self.pid, os.WNOHANG)
                    if pid_result == self.pid:
                        if os.WIFEXITED(status):
                            self.exit_code = os.WEXITSTATUS(status)
                        elif os.WIFSIGNALED(status):
                            signal_num = os.WTERMSIG(status)
                            self.exit_code = 128 + signal_num
                        else:
                            self.exit_code = 1
                    else:
                        # Process was already reaped, use stored exit code or default
                        if self.exit_code is None:
                            self.exit_code = 0 if not self._termination_initiated else 137
                except OSError:
                    # Couldn't get exit code, use reasonable default
                    if self.exit_code is None:
                        self.exit_code = 0 if not self._termination_initiated else 137
                        
                return self.exit_code


class HTProcess:
    """
    A wrapper around a process started with the 'ht' tool that provides
    methods for interacting with the process and capturing its output.

    This version leverages --start-on-output to avoid race conditions.
    """

    def __init__(
        self,
        ht_proc: subprocess.Popen,
        event_queue: queue.Queue,
        command: Optional[str] = None,
        pid: Optional[int] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        no_exit: bool = False,
    ) -> None:
        self.ht_proc = ht_proc  # The ht process itself
        self.subprocess_controller = SubprocessController(pid)
        self.event_queue = event_queue
        self.command = command
        self.output_events: List[Dict[str, Any]] = []
        self.unknown_events: List[Dict[str, Any]] = []
        self.latest_snapshot: Optional[str] = None
        self.start_time = time.time()
        self.exit_code: Optional[int] = None
        self.rows = rows
        self.cols = cols
        self.no_exit = no_exit
        self.subprocess_exited = False
        
        # Add logging for process tracking
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"HTProcess created: ht_proc.pid={ht_proc.pid}, command={command}")
        
    def __del__(self):
        """Destructor to warn about uncleaned processes."""
        if hasattr(self, 'ht_proc') and self.ht_proc and self.ht_proc.poll() is None:
            self.logger.warning(f"HTProcess being garbage collected with running ht process (PID: {self.ht_proc.pid}). This may cause resource leaks!")
            # Try emergency cleanup
            try:
                self.ht_proc.terminate()
            except Exception:
                pass

    def get_output(self) -> List[Dict[str, Any]]:
        """Return list of output events."""
        return [event for event in self.output_events if event.get("type") == "output"]

    def send_keys(self, keys: Union[KeyInput, List[KeyInput]]) -> None:
        """
        Send keys to the terminal.
        
        Since we use --start-on-output, this is much more reliable than the original.
        """
        key_strings = keys_to_strings(keys)

        if self.ht_proc.stdin is not None:
            message = json.dumps({"type": "sendKeys", "keys": key_strings})
            self.ht_proc.stdin.write(message + "\n")
            self.ht_proc.stdin.flush()
        
        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

    def snapshot(self, timeout: float = DEFAULT_SNAPSHOT_TIMEOUT) -> SnapshotResult:
        """
        Take a snapshot of the terminal output.
        """
        if self.ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self.ht_proc.returncode}")

        try:
            if self.ht_proc.stdin is not None:
                message = json.dumps({"type": "takeSnapshot"})
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
            else:
                raise RuntimeError("ht process stdin is not available")
        except BrokenPipeError as e:
            raise RuntimeError(
                f"Cannot communicate with ht process (broken pipe). "
                f"Process may have exited. Poll result: {self.ht_proc.poll()}"
            ) from e

        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        # Process events until we find the snapshot
        retry_count = 0
        while retry_count < MAX_SNAPSHOT_RETRIES:
            try:
                event = self.event_queue.get(block=True, timeout=SNAPSHOT_RETRY_TIMEOUT)
            except queue.Empty:
                retry_count += 1
                continue

            if event["type"] == "snapshot":
                data = event["data"]
                snapshot_text = data["text"]
                raw_seq = data["seq"]

                # Convert to HTML with ANSI color support
                html = simple_ansi_to_html(raw_seq)

                return SnapshotResult(
                    text=snapshot_text,
                    html=html,
                    raw_seq=raw_seq,
                )
            elif event["type"] == "output":
                self.output_events.append(event)
            elif event["type"] == "pid":
                if self.subprocess_controller.pid is None:
                    self.subprocess_controller.pid = event["data"]["pid"]
            elif event["type"] == "exitCode":
                self.subprocess_exited = True
                self.subprocess_controller.exit_code = event.get("data", {}).get("exitCode")
            elif event["type"] == "resize":
                if "data" in event:
                    data = event["data"]
                    if "rows" in data:
                        self.rows = data["rows"]
                    if "cols" in data:
                        self.cols = data["cols"]
            elif event["type"] == "init":
                pass
            else:
                self.unknown_events.append(event)

        raise RuntimeError(
            f"Failed to receive snapshot event after {MAX_SNAPSHOT_RETRIES} attempts. "
            f"ht process may have exited or stopped responding."
        )

    def exit(self, timeout: float = DEFAULT_EXIT_TIMEOUT) -> int:
        """
        Exit the ht process, ensuring clean shutdown.
        """
        self.logger.info(f"Exiting HTProcess: ht_proc.pid={self.ht_proc.pid}")
        
        # Step 1: Ensure subprocess is terminated first if needed
        if self.subprocess_controller.pid:
            self.logger.info(f"Terminating subprocess: pid={self.subprocess_controller.pid}")
            try:
                os.kill(self.subprocess_controller.pid, 0)
                self.subprocess_controller.terminate()
                try:
                    self.subprocess_controller.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
                    self.logger.info(f"Subprocess {self.subprocess_controller.pid} terminated successfully")
                except Exception:
                    self.logger.warning(f"Subprocess {self.subprocess_controller.pid} did not terminate gracefully, killing")
                    try:
                        self.subprocess_controller.kill()
                    except Exception:
                        pass
            except OSError:
                self.logger.info(f"Subprocess {self.subprocess_controller.pid} already exited")
                pass  # Process already exited

        # Step 2: Handle ht process exit
        if self.no_exit:
            time.sleep(SUBPROCESS_EXIT_DETECTION_DELAY)
            from .keys import Press
            self.send_keys([Press.ENTER])
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        # Step 3: Wait for the ht process to finish
        start_time = time.time()
        while self.ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # Timeout - force terminate
                self.logger.warning(f"ht process {self.ht_proc.pid} did not exit within timeout, terminating")
                self.ht_proc.terminate()
                try:
                    self.ht_proc.wait(timeout=DEFAULT_GRACEFUL_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"ht process {self.ht_proc.pid} did not terminate gracefully, killing")
                    self.ht_proc.kill()
                    self.ht_proc.wait()
                break
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self.exit_code = self.ht_proc.returncode
        if self.exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        self.logger.info(f"HTProcess exited successfully: exit_code={self.exit_code}")
        return self.exit_code

    def terminate(self) -> None:
        """Terminate the ht process itself."""
        try:
            self.ht_proc.terminate()
        except Exception:
            pass

    def kill(self) -> None:
        """Force kill the ht process itself."""
        try:
            self.ht_proc.kill()
        except Exception:
            pass

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """
        Wait for the ht process itself to finish.
        """
        try:
            if timeout is None:
                self.exit_code = self.ht_proc.wait()
            else:
                self.exit_code = self.ht_proc.wait(timeout=timeout)
            return self.exit_code
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None



def run(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
) -> HTProcess:
    """
    Run a command using the 'ht' tool and return a HTProcess object.
    
    This version uses --start-on-output by default to avoid race conditions.
    """
    ht_binary = find_ht_bin()
    
    # Handle both string commands and pre-split argument lists
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command

    # Create a queue for events
    event_queue: queue.Queue = queue.Queue()

    # Build the ht command with event subscription
    ht_cmd_args = [
        ht_binary,
        "--subscribe",
        "init,snapshot,output,resize,pid,exitCode",
    ]

    # Add size options if specified
    if rows is not None and cols is not None:
        ht_cmd_args.extend(["--size", f"{cols}x{rows}"])

    # Add no-exit option if specified
    if no_exit:
        ht_cmd_args.append("--no-exit")
        
    # Always use --start-on-output to avoid race conditions
    ht_cmd_args.append("--start-on-output")

    # Add separator and the command to run
    ht_cmd_args.append("--")
    ht_cmd_args.extend(cmd_args)

    # Launch ht
    ht_proc = subprocess.Popen(
        ht_cmd_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Create a reader thread to capture ht output
    def reader_thread(
        ht_proc: subprocess.Popen,
        queue_obj: queue.Queue,
        ht_process: HTProcess,
    ) -> None:
        while True:
            if ht_proc.stdout is None:
                break
            line = ht_proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                queue_obj.put(event)

                if event["type"] == "output":
                    ht_process.output_events.append(event)
                elif event["type"] == "exitCode":
                    ht_process.subprocess_exited = True
                    if hasattr(ht_process, "subprocess_controller"):
                        exit_code = event.get("data", {}).get("exitCode")
                        if exit_code is not None:
                            ht_process.subprocess_controller.exit_code = exit_code
            except json.JSONDecodeError:
                # Skip non-JSON lines
                pass

    # Create an HTProcess instance
    process = HTProcess(
        ht_proc,
        event_queue,
        command=" ".join(cmd_args),
        rows=rows,
        cols=cols,
        no_exit=no_exit,
    )

    # Start the reader thread
    thread = threading.Thread(target=reader_thread, args=(ht_proc, event_queue, process), daemon=True)
    thread.start()
    
    # Wait briefly for the process to initialize and get PID
    start_time = time.time()
    while time.time() - start_time < 2:
        try:
            event = event_queue.get(block=True, timeout=0.5)
            if event["type"] == "pid":
                pid = event["data"]["pid"]
                process.subprocess_controller.pid = pid
                break
        except queue.Empty:
            continue

    time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
    return process


@contextmanager
def ht_process(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
):
    """
    Context manager for HTProcess that ensures proper cleanup.
    """
    proc = run(command, rows=rows, cols=cols, no_exit=no_exit)
    try:
        yield proc
    finally:
        try:
            if proc.subprocess_controller.pid:
                proc.subprocess_controller.terminate()
                proc.subprocess_controller.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception:
            try:
                if proc.subprocess_controller.pid:
                    proc.subprocess_controller.kill()
            except Exception:
                pass

        try:
            proc.terminate()
            proc.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
