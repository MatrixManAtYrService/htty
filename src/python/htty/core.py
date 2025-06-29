"""
Core htty functionality for terminal automation.

This module provides the main HTProcess class for running and interacting with
terminal applications through a headless terminal interface.

# Test comment to verify build optimization works
"""

import json
import logging
import os
import queue
import signal
import subprocess
import threading
import time
from contextlib import contextmanager, suppress
from typing import Any, Dict, List, Optional, Union

from ._find_ht import find_ht_bin
from .html_utils import simple_ansi_to_html
from .keys import KeyInput, keys_to_strings

# Get default logger for this module
default_logger = logging.getLogger(__name__)

__all__ = [
    "SnapshotResult",
    "SubprocessController",
    "HTProcess",
    "run",
    "terminal_session",
    "get_ht_help",
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

    def wait(self, timeout: Optional[float] = 5.0) -> Optional[int]:
        """
        Wait for the subprocess to finish.

        Args:
            timeout: Maximum time to wait (in seconds). Defaults to 5.0 seconds.

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

    This version leverages --wait-for-output to avoid race conditions.
    """

    def __init__(
        self,
        ht_proc: subprocess.Popen[str],
        event_queue: queue.Queue[Dict[str, Any]],
        command: Optional[str] = None,
        pid: Optional[int] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        no_exit: bool = False,
        logger: Optional[logging.Logger] = None,
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
        self.subprocess_completed = False  # Set earlier when command completion is detected

        # Use provided logger or fall back to default
        self.logger = logger or default_logger
        self.logger.debug(f"HTProcess created: ht_proc.pid={ht_proc.pid}, command={command}")

    def __del__(self):
        """Destructor to warn about uncleaned processes."""
        if hasattr(self, "ht_proc") and self.ht_proc and self.ht_proc.poll() is None:
            self.logger.warning(
                f"HTProcess being garbage collected with running ht process (PID: {self.ht_proc.pid}). "
                f"This may cause resource leaks!"
            )
            # Try emergency cleanup
            with suppress(Exception):
                self.ht_proc.terminate()

    def get_output(self) -> List[Dict[str, Any]]:
        """Return list of output events."""
        return [event for event in self.output_events if event.get("type") == "output"]

    def send_keys(self, keys: Union[KeyInput, List[KeyInput]]) -> None:
        """
        Send keys to the terminal.

        Since we use --wait-for-output, this is much more reliable than the original.
        """
        key_strings = keys_to_strings(keys)
        message = json.dumps({"type": "sendKeys", "keys": key_strings})

        self.logger.debug(f"Sending keys: {message}")

        if self.ht_proc.stdin is not None:
            try:
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
                self.logger.debug("Keys sent successfully")
            except (BrokenPipeError, OSError) as e:
                self.logger.error(f"Failed to send keys: {e}")
                self.logger.error(f"ht process poll result: {self.ht_proc.poll()}")
                raise
        else:
            self.logger.error("ht process stdin is None")

        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

    def snapshot(self, timeout: float = DEFAULT_SNAPSHOT_TIMEOUT) -> SnapshotResult:
        """
        Take a snapshot of the terminal output.
        """
        if self.ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self.ht_proc.returncode}")

        message = json.dumps({"type": "takeSnapshot"})
        self.logger.debug(f"Taking snapshot: {message}")

        try:
            if self.ht_proc.stdin is not None:
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
                self.logger.debug("Snapshot request sent successfully")
            else:
                raise RuntimeError("ht process stdin is not available")
        except BrokenPipeError as e:
            self.logger.error(f"Failed to send snapshot request: {e}")
            self.logger.error(f"ht process poll result: {self.ht_proc.poll()}")
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

        Uses different strategies based on subprocess state:
        - If subprocess already exited (exitCode event received): graceful shutdown via exit command
        - If subprocess still running: forced termination with SIGTERM then SIGKILL
        """
        self.logger.debug(f"Exiting HTProcess: ht_proc.pid={self.ht_proc.pid}")

        # Check if we've already received the exitCode event
        if self.subprocess_exited:
            self.logger.debug("Subprocess already exited (exitCode event received), attempting graceful shutdown")
            return self._graceful_exit(timeout)
        else:
            self.logger.debug("Subprocess has not exited yet, checking current state")

            # Give a brief moment for any pending exitCode event to arrive
            brief_wait_start = time.time()
            while time.time() - brief_wait_start < 0.5:  # Wait up to 500ms
                if self.subprocess_exited:
                    self.logger.debug("Subprocess exited during brief wait, attempting graceful shutdown")
                    return self._graceful_exit(timeout)
                time.sleep(0.01)

            self.logger.debug("Subprocess still running after brief wait, using forced termination")
            return self._forced_exit(timeout)

    def _graceful_exit(self, timeout: float) -> int:
        """
        Graceful exit: subprocess has completed, so we can send exit command to ht process.
        """
        # Send exit command to ht process
        message = json.dumps({"type": "exit"})
        self.logger.debug(f"Sending exit command to ht process {self.ht_proc.pid}: {message}")

        try:
            if self.ht_proc.stdin is not None:
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
                self.logger.debug(f"Exit command sent successfully to ht process {self.ht_proc.pid}")
                self.ht_proc.stdin.close()  # Close stdin after sending exit command
                self.logger.debug(f"Closed stdin for ht process {self.ht_proc.pid}")
            else:
                self.logger.debug(f"ht process {self.ht_proc.pid} stdin is None, cannot send exit command")
        except (BrokenPipeError, OSError) as e:
            self.logger.debug(
                f"Failed to send exit command to ht process {self.ht_proc.pid}: {e} (process may have already exited)"
            )
            pass

        # Wait for the ht process to finish gracefully
        start_time = time.time()
        while self.ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # Graceful exit timed out, fall back to forced termination
                self.logger.warning(
                    f"ht process {self.ht_proc.pid} did not exit gracefully within timeout, "
                    f"falling back to forced termination"
                )
                return self._forced_exit(timeout)
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self.exit_code = self.ht_proc.returncode
        if self.exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        self.logger.debug(f"HTProcess exited gracefully: exit_code={self.exit_code}")
        return self.exit_code

    def _forced_exit(self, timeout: float) -> int:
        """
        Forced exit: subprocess may still be running, so we need to terminate everything forcefully.
        """
        # Step 1: Ensure subprocess is terminated first if needed
        if self.subprocess_controller.pid and not self.subprocess_exited:
            self.logger.debug(f"Terminating subprocess: pid={self.subprocess_controller.pid}")
            try:
                os.kill(self.subprocess_controller.pid, 0)
                self.subprocess_controller.terminate()
                try:
                    self.subprocess_controller.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
                    self.logger.debug(f"Subprocess {self.subprocess_controller.pid} terminated successfully")
                except Exception:
                    self.logger.warning(
                        f"Subprocess {self.subprocess_controller.pid} did not terminate gracefully, killing"
                    )
                    with suppress(Exception):
                        self.subprocess_controller.kill()
            except OSError:
                self.logger.debug(f"Subprocess {self.subprocess_controller.pid} already exited")
                pass  # Process already exited

        # Step 2: Force terminate the ht process with SIGTERM, then SIGKILL if needed
        self.logger.debug(f"Force terminating ht process {self.ht_proc.pid}")

        # Try SIGTERM first
        try:
            self.ht_proc.terminate()
            self.logger.debug(f"Sent SIGTERM to ht process {self.ht_proc.pid}")
        except Exception as e:
            self.logger.debug(f"Failed to send SIGTERM to ht process {self.ht_proc.pid}: {e}")

        # Wait for termination
        start_time = time.time()
        while self.ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # SIGTERM timeout, try SIGKILL
                self.logger.warning(
                    f"ht process {self.ht_proc.pid} did not terminate with SIGTERM within timeout, sending SIGKILL"
                )
                try:
                    self.ht_proc.kill()
                    self.logger.debug(f"Sent SIGKILL to ht process {self.ht_proc.pid}")
                except Exception as e:
                    self.logger.debug(f"Failed to send SIGKILL to ht process {self.ht_proc.pid}: {e}")

                # Wait for SIGKILL to take effect
                kill_start_time = time.time()
                while self.ht_proc.poll() is None:
                    if time.time() - kill_start_time > timeout:
                        self.logger.error(f"ht process {self.ht_proc.pid} did not respond to SIGKILL within timeout")
                        break
                    time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
                break
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self.exit_code = self.ht_proc.returncode
        if self.exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        self.logger.debug(f"HTProcess exited via forced termination: exit_code={self.exit_code}")
        return self.exit_code

    def terminate(self) -> None:
        """Terminate the ht process itself."""
        with suppress(Exception):
            self.ht_proc.terminate()

    def kill(self) -> None:
        """Force kill the ht process itself."""
        with suppress(Exception):
            self.ht_proc.kill()

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


def get_ht_help() -> str:
    """Get the help output from the ht binary."""
    ht_binary = find_ht_bin()
    try:
        result = subprocess.run([ht_binary, "--help"], capture_output=True, text=True, timeout=10)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: ht --help timed out"
    except Exception as e:
        return f"Error getting ht help: {e}"


def run(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
    logger: Optional[logging.Logger] = None,
    extra_subscribes: Optional[List[str]] = None,
) -> HTProcess:
    """
    Run a command using the 'ht' tool and return a HTProcess object.

    This version uses --wait-for-output by default to avoid race conditions.
    """
    # Use provided logger or fall back to default
    process_logger = logger or default_logger

    ht_binary = find_ht_bin()

    # Handle both string commands and pre-split argument lists
    cmd_args = command.split() if isinstance(command, str) else command

    # Create a queue for events
    event_queue: queue.Queue[Dict[str, Any]] = queue.Queue()

    # Build the ht command with event subscription
    base_subscribes = ["init", "snapshot", "output", "resize", "pid", "exitCode", "commandCompleted"]
    if extra_subscribes:
        base_subscribes.extend(extra_subscribes)

    ht_cmd_args = [
        ht_binary,
        "--subscribe",
        ",".join(base_subscribes),
    ]

    # Add size options if specified
    if rows is not None and cols is not None:
        ht_cmd_args.extend(["--size", f"{cols}x{rows}"])

    # Note: --no-exit and --wait-for-output options are not supported in this version
    # They've been removed from this implementation

    # Add separator and the command to run
    ht_cmd_args.append("--")
    ht_cmd_args.extend(cmd_args)

    # Launch ht with debug logging
    process_logger.debug(f"Launching: {' '.join(ht_cmd_args)}")

    ht_proc = subprocess.Popen(
        ht_cmd_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    process_logger.debug(f"ht started: PID {ht_proc.pid}")

    # Create a reader thread to capture ht output
    def reader_thread(
        ht_proc: subprocess.Popen[str],
        queue_obj: queue.Queue[Dict[str, Any]],
        ht_process: HTProcess,
        thread_logger: logging.Logger,
    ) -> None:
        thread_logger.debug(f"Reader thread started for ht process {ht_proc.pid}")

        while True:
            if ht_proc.stdout is None:
                thread_logger.warning(f"ht process {ht_proc.pid} stdout is None, exiting reader thread")
                break

            line = ht_proc.stdout.readline()
            if not line:
                thread_logger.debug(f"ht process {ht_proc.pid} stdout closed, exiting reader thread")
                break

            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                thread_logger.debug(f"ht event: {event}")
                queue_obj.put(event)

                if event["type"] == "output":
                    ht_process.output_events.append(event)
                elif event["type"] == "exitCode":
                    thread_logger.debug(
                        f"ht process {ht_proc.pid} subprocess exited with code: {event.get('data', {}).get('exitCode')}"
                    )
                    ht_process.subprocess_exited = True
                    if hasattr(ht_process, "subprocess_controller"):
                        exit_code = event.get("data", {}).get("exitCode")
                        if exit_code is not None:
                            ht_process.subprocess_controller.exit_code = exit_code
                elif event["type"] == "pid":
                    thread_logger.debug(f"ht process {ht_proc.pid} subprocess PID: {event.get('data', {}).get('pid')}")
                elif event["type"] == "commandCompleted":
                    # Command has completed - this is the reliable signal that subprocess finished
                    ht_process.subprocess_completed = True
                elif event["type"] == "debug":
                    thread_logger.debug(f"ht process {ht_proc.pid} debug: {event.get('data', {})}")
                    # Note: We no longer rely on debug events for subprocess_completed
                    # The commandCompleted event (above) is the reliable source
            except json.JSONDecodeError as e:
                # Only log raw stdout when we can't parse it as JSON - this indicates an unexpected message
                thread_logger.warning(f"ht process {ht_proc.pid} non-JSON stdout: {line} (error: {e})")
                pass

        thread_logger.debug(f"Reader thread exiting for ht process {ht_proc.pid}")

    # Create an HTProcess instance
    process = HTProcess(
        ht_proc,
        event_queue,
        command=" ".join(cmd_args),
        rows=rows,
        cols=cols,
        no_exit=no_exit,
        logger=process_logger,
    )

    # Start the reader thread for stdout
    stdout_thread = threading.Thread(
        target=reader_thread, args=(ht_proc, event_queue, process, process_logger), daemon=True
    )
    stdout_thread.start()

    # Start a stderr reader thread
    def stderr_reader_thread(ht_proc: subprocess.Popen[str], thread_logger: logging.Logger) -> None:
        thread_logger.debug(f"Stderr reader thread started for ht process {ht_proc.pid}")

        while True:
            if ht_proc.stderr is None:
                thread_logger.warning(f"ht process {ht_proc.pid} stderr is None, exiting stderr reader thread")
                break

            line = ht_proc.stderr.readline()
            if not line:
                thread_logger.debug(f"ht process {ht_proc.pid} stderr closed, exiting stderr reader thread")
                break

            line = line.strip()
            if line:
                thread_logger.debug(f"ht stderr: {line}")

        thread_logger.debug(f"Stderr reader thread exiting for ht process {ht_proc.pid}")

    stderr_thread = threading.Thread(target=stderr_reader_thread, args=(ht_proc, process_logger), daemon=True)
    stderr_thread.start()

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
def terminal_session(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
    logger: Optional[logging.Logger] = None,
    extra_subscribes: Optional[List[str]] = None,
):
    """
    Context manager for HTProcess that ensures proper cleanup.
    """
    proc = run(command, rows=rows, cols=cols, no_exit=no_exit, logger=logger, extra_subscribes=extra_subscribes)
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
            with suppress(Exception):
                proc.kill()
