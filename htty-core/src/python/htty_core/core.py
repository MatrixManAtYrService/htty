"""
Core htty-ht functionality for terminal automation.

This module provides the main HTProcess class with bundled ht binary.
"""

import json
import logging
import os
import queue
import signal
import subprocess
import threading
import time
import sys
import sysconfig
from typing import Any, Dict, List, Optional, Union

# Get default logger for this module
default_logger = logging.getLogger(__name__)

__all__ = [
    "HTProcess",
    "create_process",
    "find_ht_binary",
]

# Constants
DEFAULT_SLEEP_AFTER_KEYS = 0.1
DEFAULT_SUBPROCESS_WAIT_TIMEOUT = 2.0
DEFAULT_SNAPSHOT_TIMEOUT = 5.0
DEFAULT_EXIT_TIMEOUT = 5.0
DEFAULT_GRACEFUL_TERMINATION_TIMEOUT = 5.0
SNAPSHOT_RETRY_TIMEOUT = 0.5
SUBPROCESS_EXIT_DETECTION_DELAY = 0.5
MAX_SNAPSHOT_RETRIES = 10


def find_ht_binary() -> str:
    """Find the bundled ht binary."""

    # Check HTTY_HT_BIN environment variable first
    env_path = os.environ.get("HTTY_HT_BIN")
    if env_path and os.path.isfile(env_path):
        return env_path

    ht_exe = "ht" + sysconfig.get_config_var("EXE")

    # Check standard script directory first (where maturin puts binaries)
    path = os.path.join(sysconfig.get_path("scripts"), ht_exe)
    if os.path.isfile(path):
        return path

    # Check user-specific scheme locations
    if sys.version_info >= (3, 10):
        user_scheme = sysconfig.get_preferred_scheme("user")
    elif os.name == "nt":
        user_scheme = "nt_user"
    elif sys.platform == "darwin" and getattr(sys, "_framework", None):
        user_scheme = "osx_framework_user"
    else:
        user_scheme = "posix_user"

    path = os.path.join(sysconfig.get_path("scripts", scheme=user_scheme), ht_exe)
    if os.path.isfile(path):
        return path

    # Search in `bin` adjacent to package root (as created by `pip install --target`)
    pkg_root = os.path.dirname(os.path.dirname(__file__))
    target_path = os.path.join(pkg_root, "bin", ht_exe)
    if os.path.isfile(target_path):
        return target_path

    # Fallback: search in PATH
    import shutil

    path_ht = shutil.which("ht")
    if path_ht and os.path.isfile(path_ht):
        return path_ht

    raise FileNotFoundError(
        f"ht binary not found. Searched: {path}, {target_path}, PATH"
    )


class SnapshotResult:
    """Result of taking a terminal snapshot."""

    def __init__(self, text: str, html: str, raw_seq: str):
        self.text = text
        self.html = html
        self.raw_seq = raw_seq


class SubprocessController:
    """Controls the subprocess running in the terminal."""

    def __init__(self):
        self.pid: Optional[int] = None
        self.exit_code: Optional[int] = None

    def terminate(self):
        """Terminate the subprocess if it's running."""
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass  # Process already dead


class HTProcess:
    """
    Manages a headless terminal process for automation.

    This class provides a high-level interface for running commands in a headless
    terminal and interacting with them programmatically.
    """

    def __init__(
        self,
        command: Union[str, List[str]],
        rows: int = 24,
        cols: int = 80,
        logger: Optional[logging.Logger] = None,
        extra_subscribes: Optional[List[str]] = None,
    ):
        self.command = command
        self.rows = rows
        self.cols = cols
        self.logger = logger or default_logger
        self.extra_subscribes = extra_subscribes or []

        self.ht_proc: Optional[subprocess.Popen] = None
        self.subprocess_controller = SubprocessController()
        self.subprocess_exited = False
        self.subprocess_completed = False

        # Event handling
        self.event_queue: queue.Queue = queue.Queue()
        self.output_events: List[Dict[str, Any]] = []
        self.unknown_events: List[Dict[str, Any]] = []

        # Start the ht process
        self._start_ht_process()

    def _start_ht_process(self):
        """Start the ht subprocess."""
        ht_binary = find_ht_binary()

        # Build command arguments
        cmd_args = [ht_binary]

        # Add subscription arguments
        subscribes = [
            "init",
            "snapshot",
            "output",
            "resize",
            "pid",
            "exitCode",
            "commandCompleted",
        ]
        subscribes.extend(self.extra_subscribes)
        cmd_args.extend(["--subscribe", ",".join(subscribes)])

        # Add size arguments
        cmd_args.extend(["--size", f"{self.cols}x{self.rows}"])

        # Add the command to run
        cmd_args.append("--")
        if isinstance(self.command, str):
            cmd_args.extend(self.command.split())
        else:
            cmd_args.extend(self.command)

        self.logger.debug(f"Launching: {' '.join(cmd_args)}")

        # Start the process
        self.ht_proc = subprocess.Popen(
            cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )

        self.logger.debug(f"ht started: PID {self.ht_proc.pid}")

        # Start reader threads
        self._start_reader_threads()

    def _start_reader_threads(self):
        """Start threads to read from ht process stdout/stderr."""
        if self.ht_proc is None:
            raise RuntimeError("ht process not started")

        def read_stdout():
            if self.ht_proc is None:
                raise RuntimeError(
                    "ht_proc is None - process was not properly initialized"
                )
            self.logger.debug(
                f"Reader thread started for ht process {self.ht_proc.pid}"
            )
            try:
                while self.ht_proc.poll() is None:
                    if self.ht_proc.stdout:
                        line = self.ht_proc.stdout.readline()
                        if line:
                            try:
                                event = json.loads(line.strip())
                                self.event_queue.put(event)
                            except json.JSONDecodeError as e:
                                self.logger.warning(
                                    f"Failed to parse JSON from ht: {line.strip()}: {e}"
                                )
            except Exception as e:
                self.logger.error(f"Error in stdout reader thread: {e}")

        def read_stderr():
            if self.ht_proc is None:
                raise RuntimeError(
                    "ht_proc is None - process was not properly initialized"
                )
            self.logger.debug(
                f"Stderr reader thread started for ht process {self.ht_proc.pid}"
            )
            try:
                while self.ht_proc.poll() is None:
                    if self.ht_proc.stderr:
                        line = self.ht_proc.stderr.readline()
                        if line:
                            self.logger.debug(f"ht stderr: {line.strip()}")
            except Exception as e:
                self.logger.error(f"Error in stderr reader thread: {e}")

        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()

    def snapshot(self, timeout: float = DEFAULT_SNAPSHOT_TIMEOUT) -> SnapshotResult:
        """Take a snapshot of the terminal output."""
        if self.ht_proc is None or self.ht_proc.poll() is not None:
            raise RuntimeError(
                f"ht process has exited with code {self.ht_proc.returncode if self.ht_proc else 'unknown'}"
            )

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
            raise RuntimeError(
                "Cannot communicate with ht process (broken pipe). Process may have exited."
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

                # Simple HTML conversion (can be enhanced later)
                html = raw_seq  # For now, just use raw sequence

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
                self.subprocess_controller.exit_code = event.get("data", {}).get(
                    "exitCode"
                )
            elif event["type"] == "commandCompleted":
                self.subprocess_completed = True
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

    def send_keys(self, keys: List[str]):
        """Send key sequences to the terminal."""
        if self.ht_proc is None or self.ht_proc.poll() is not None:
            raise RuntimeError("ht process is not running")

        message = json.dumps({"type": "sendKeys", "keys": keys})
        self.logger.debug(f"Sending keys: {message}")

        try:
            if self.ht_proc.stdin is not None:
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
                self.logger.debug("Keys sent successfully")
            else:
                raise RuntimeError("ht process stdin is not available")
        except BrokenPipeError as e:
            raise RuntimeError(
                "Cannot communicate with ht process (broken pipe)"
            ) from e

        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

    def exit(self, timeout: float = DEFAULT_EXIT_TIMEOUT) -> int:
        """Exit the ht process and return exit code."""
        if self.ht_proc is None:
            return 0

        # Try graceful exit first
        try:
            if self.ht_proc.stdin and self.ht_proc.poll() is None:
                message = json.dumps({"type": "exit"})
                self.ht_proc.stdin.write(message + "\n")
                self.ht_proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass  # Process may have already exited

        # Wait for process to exit
        try:
            return_code = self.ht_proc.wait(timeout=timeout)
            return return_code
        except subprocess.TimeoutExpired:
            # Force termination
            self.ht_proc.terminate()
            try:
                return_code = self.ht_proc.wait(timeout=2)
                return return_code
            except subprocess.TimeoutExpired:
                self.ht_proc.kill()
                return self.ht_proc.wait()


def create_process(
    command: Union[str, List[str]],
    rows: int = 24,
    cols: int = 80,
    logger: Optional[logging.Logger] = None,
    extra_subscribes: Optional[List[str]] = None,
) -> HTProcess:
    """
    Create and return a new HTProcess.

    This is a convenience function for creating HTProcess instances.
    """
    return HTProcess(
        command=command,
        rows=rows,
        cols=cols,
        logger=logger,
        extra_subscribes=extra_subscribes,
    )
