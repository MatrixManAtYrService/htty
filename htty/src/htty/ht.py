import json
import logging
import os
import queue
import re
import shlex
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Annotated, Any, Optional, TypeAlias, Union

from htty_core import (
    Cols,
    Command,
    HtArgs,
    HtEvent,
    Rows,
    run as htty_core_run,
)
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from .constants import (
    DEFAULT_EXIT_TIMEOUT,
    DEFAULT_EXPECT_TIMEOUT,
    DEFAULT_SLEEP_AFTER_KEYS,
    DEFAULT_SNAPSHOT_TIMEOUT,
    DEFAULT_SUBPROCESS_WAIT_TIMEOUT,
    SNAPSHOT_RETRY_TIMEOUT,
)
from .html_utils import simple_ansi_to_html
from .keys import KeyInput, keys_to_strings
from .proc import CmdProcess, HtProcess, ProcessController

# Get default logger for this module
default_logger = logging.getLogger(__name__)


class SnapshotNotReady(Exception):
    """Exception raised when snapshot is not yet available from the queue."""

    pass


__all__ = [
    "terminal_session",
    "SnapshotResult",
    "HtWrapper",
    "ProcessController",
    "run",
]

NoExit: TypeAlias = Annotated[
    bool,
    (
        "whether to keep ht running even after the underlying command exits\n"
        "allows the caller to take snapshots even after the command has completed\n"
        "requires the caller to send an explicit 'exit' event to cause ht to exit\n"
    ),
]
Logger: TypeAlias = Annotated[Optional[logging.Logger], "callers can override the default logger with their own"]

ExtraSubscribes: TypeAlias = Annotated[Optional[list[HtEvent]], "additional event types to subscribe to"]


class SnapshotResult:
    """Result of taking a terminal snapshot"""

    def __init__(self, text: str, html: str, raw_seq: str):
        self.text = text
        self.html = html
        self.raw_seq = raw_seq

    def __repr__(self):
        return f"SnapshotResult(text={self.text!r}, html=<{len(self.html)} chars>, raw_seq=<{len(self.raw_seq)} chars>)"


class HtWrapper:
    """
    A wrapper around a process started with the 'ht' tool that provides
    methods for interacting with the process and capturing its output.
    """

    ht: ProcessController
    """
    Helpers for interacting with the `ht` process (a child process of the python
    that called `htty.run` or `htty.terminal_session`)
    """

    cmd: ProcessController
    """
    Helpers for interacting with the shell that wraps the caller's command (`ht`'s child process)
    """

    def __init__(
        self,
        ht_proc: "subprocess.Popen[str]",
        event_queue: queue.Queue[dict[str, Any]],
        command: Optional[str] = None,
        pid: Optional[int] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        no_exit: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        @private
        Users are not expect to create these directly.
        They should use `with terminal_session(...)` or `run(...)`
        """
        self._ht_proc = ht_proc  # The ht process itself
        self._cmd_process = CmdProcess(pid)
        self._event_queue = event_queue
        self._command = command
        self._output_events: list[dict[str, Any]] = []
        self._unknown_events: list[dict[str, Any]] = []
        self._latest_snapshot: Optional[str] = None
        self._start_time = time.time()
        self._exit_code: Optional[int] = None
        self._rows = rows
        self._cols = cols
        self._no_exit = no_exit
        self._subprocess_exited = False
        self._subprocess_completed = False  # Set earlier when command completion is detected

        # Use provided logger or fall back to default
        self._logger = logger or default_logger
        self._logger.debug(f"HTProcess created: ht_proc.pid={ht_proc.pid}, command={command}")

        # Create the public interface objects
        self.ht: ProcessController = HtProcess(ht_proc, self)
        self.cmd: ProcessController = self._cmd_process

    def __del__(self):
        """Destructor to warn about uncleaned processes."""
        if hasattr(self, "_ht_proc") and self._ht_proc and self._ht_proc.poll() is None:
            self._logger.warning(
                f"HTProcess being garbage collected with running ht process (PID: {self._ht_proc.pid}). "
                f"This may cause resource leaks!"
            )
            # Try emergency cleanup
            with suppress(Exception):
                self._ht_proc.terminate()

    def get_output(self) -> list[dict[str, Any]]:
        """
        Return list of [output](./htty-core/htty_core.html#HtEvent.OUTPUT) events."""
        return [event for event in self._output_events if event.get("type") == "output"]

    def add_output_event(self, event: dict[str, Any]) -> None:
        """
        @private
        Add an output event (for internal use by reader thread).
        """
        self._output_events.append(event)

    def set_subprocess_exited(self, exited: bool) -> None:
        """
        @private
        Set subprocess exited flag (for internal use by reader thread).
        """
        self._subprocess_exited = exited

    def set_subprocess_completed(self, completed: bool) -> None:
        """
        @private
        Set subprocess completed flag (for internal use by reader thread).
        """
        self._subprocess_completed = completed
        self._cmd_process.set_completed(completed)

    def send_keys(self, keys: Union[KeyInput, list[KeyInput]]) -> None:
        """
        Send keys to the terminal.  Accepts strings, `Press` objects, and lists of strings or `Press` objects.
        For keys that you can `Press`, see
        [keys.py](https://github.com/MatrixManAtYrService/htty/blob/main/htty/src/htty/keys.py).

        ```python
        from htty import Press, terminal_session

        with (
            terminal_session("sh -i", rows=4, cols=40, logger=test_logger) as sh,
        ):
            sh.send_keys("echo foo && sleep 999")
            sh.send_keys(Press.ENTER)
            sh.expect("^foo")
            sh.send_keys(Press.CTRL_Z)
            sh.expect("Stopped")
            sh.send_keys(["clear", Press.ENTER])
        ```

        These are sent to `ht` as events that look like this

        ```json
        {"type": "sendKeys", "keys": ["echo foo && sleep 999", "Enter"]}
        ```

        Notice that Press.ENTER is still sent as "Enter" under the hood.
        `ht` checks to see if it corresponds with a known key and sends it letter-at-a-time if not.

        Because of this, you might run into suprises if you want to type individual characters which happen to spell out
        a known key such as "Enter" or "Backspace".

        Work around this by breaking up the key names like so:

        ```python
        sh.send_keys(["Ente", "r"])
        ```

        If this behavior is problematic for you, consider submitting an issue.
        """
        key_strings = keys_to_strings(keys)
        message = json.dumps({"type": "sendKeys", "keys": key_strings})

        self._logger.debug(f"Sending keys: {message}")

        if self._ht_proc.stdin is not None:
            try:
                self._ht_proc.stdin.write(message + "\n")
                self._ht_proc.stdin.flush()
                self._logger.debug("Keys sent successfully")
            except (BrokenPipeError, OSError) as e:
                self._logger.error(f"Failed to send keys: {e}")
                self._logger.error(f"ht process poll result: {self._ht_proc.poll()}")
                raise
        else:
            self._logger.error("ht process stdin is None")

        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

    def snapshot(self, timeout: float = DEFAULT_SNAPSHOT_TIMEOUT) -> SnapshotResult:
        """
        Take a snapshot of the terminal output.
        """
        if self._ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self._ht_proc.returncode}")

        message = json.dumps({"type": "takeSnapshot"})
        self._logger.debug(f"Taking snapshot: {message}")

        try:
            if self._ht_proc.stdin is not None:
                self._ht_proc.stdin.write(message + "\n")
                self._ht_proc.stdin.flush()
                self._logger.debug("Snapshot request sent successfully")
            else:
                raise RuntimeError("ht process stdin is not available")
        except BrokenPipeError as e:
            self._logger.error(f"Failed to send snapshot request: {e}")
            self._logger.error(f"ht process poll result: {self._ht_proc.poll()}")
            raise RuntimeError(
                f"Cannot communicate with ht process (broken pipe). "
                f"Process may have exited. Poll result: {self._ht_proc.poll()}"
            ) from e

        time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        # Use tenacity to retry getting the snapshot
        return self._wait_for_snapshot(timeout)

    def _wait_for_snapshot(self, timeout: float) -> SnapshotResult:
        """
        Wait for snapshot response from the event queue with timeout and retries.
        """

        @retry(
            stop=stop_after_delay(timeout),
            wait=wait_fixed(SNAPSHOT_RETRY_TIMEOUT),
            retry=retry_if_exception_type(SnapshotNotReady),
        )
        def _get_snapshot() -> SnapshotResult:
            try:
                event = self._event_queue.get(block=True, timeout=SNAPSHOT_RETRY_TIMEOUT)
            except queue.Empty as e:
                raise SnapshotNotReady("No events available in queue") from e

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
                self._output_events.append(event)
            elif event["type"] == "resize":
                data = event.get("data", {})
                if "rows" in data:
                    self._rows = data["rows"]
                if "cols" in data:
                    self._cols = data["cols"]
            elif event["type"] == "init":
                pass
            else:
                # Put non-snapshot events back in queue for reader thread to handle
                self._event_queue.put(event)

            # If we get here, we didn't find a snapshot, so retry
            raise SnapshotNotReady(f"Received {event['type']} event, waiting for snapshot")

        try:
            return _get_snapshot()
        except Exception as e:
            # Handle both direct SnapshotNotReady and tenacity RetryError
            from tenacity import RetryError

            if isinstance(e, (SnapshotNotReady, RetryError)):
                raise RuntimeError(
                    f"Failed to receive snapshot event within {timeout} seconds. "
                    f"ht process may have exited or stopped responding."
                ) from e
            raise

    def exit(self, timeout: float = DEFAULT_EXIT_TIMEOUT) -> int:
        """
        Exit the ht process, ensuring clean shutdown.

        Uses different strategies based on subprocess state:
        - If subprocess already exited (exitCode event received): graceful shutdown via exit command
        - If subprocess still running: forced termination with SIGTERM then SIGKILL
        """
        self._logger.debug(f"Exiting HTProcess: ht_proc.pid={self._ht_proc.pid}")

        # Check if we've already received the exitCode event
        if self._subprocess_exited:
            self._logger.debug("Subprocess already exited (exitCode event received), attempting graceful shutdown")
            return self._graceful_exit(timeout)
        else:
            self._logger.debug("Subprocess has not exited yet, checking current state")

            # Give a brief moment for any pending exitCode event to arrive
            brief_wait_start = time.time()
            while time.time() - brief_wait_start < 0.5:  # Wait up to 500ms
                if self._subprocess_exited:
                    self._logger.debug("Subprocess exited during brief wait, attempting graceful shutdown")
                    return self._graceful_exit(timeout)
                time.sleep(0.01)

            self._logger.debug("Subprocess still running after brief wait, using forced termination")
            return self._forced_exit(timeout)

    def _graceful_exit(self, timeout: float) -> int:
        """
        Graceful exit: subprocess has completed, so we can send exit command to ht process.
        """
        # Send exit command to ht process
        message = json.dumps({"type": "exit"})
        self._logger.debug(f"Sending exit command to ht process {self._ht_proc.pid}: {message}")

        try:
            if self._ht_proc.stdin is not None:
                self._ht_proc.stdin.write(message + "\n")
                self._ht_proc.stdin.flush()
                self._logger.debug(f"Exit command sent successfully to ht process {self._ht_proc.pid}")
                self._ht_proc.stdin.close()  # Close stdin after sending exit command
                self._logger.debug(f"Closed stdin for ht process {self._ht_proc.pid}")
            else:
                self._logger.debug(f"ht process {self._ht_proc.pid} stdin is None, cannot send exit command")
        except (BrokenPipeError, OSError) as e:
            self._logger.debug(
                f"Failed to send exit command to ht process {self._ht_proc.pid}: {e} (process may have already exited)"
            )
            pass

        # Wait for the ht process to finish gracefully
        start_time = time.time()
        while self._ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # Graceful exit timed out, fall back to forced termination
                self._logger.warning(
                    f"ht process {self._ht_proc.pid} did not exit gracefully within timeout, "
                    f"falling back to forced termination"
                )
                return self._forced_exit(timeout)
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self._exit_code = self._ht_proc.returncode
        if self._exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        self._logger.debug(f"HTProcess exited gracefully: exit_code={self._exit_code}")
        return self._exit_code

    def _forced_exit(self, timeout: float) -> int:
        """
        Forced exit: subprocess may still be running, so we need to terminate everything forcefully.
        """
        # Step 1: Ensure subprocess is terminated first if needed
        if self._cmd_process.pid and not self._subprocess_exited:
            self._logger.debug(f"Terminating subprocess: pid={self._cmd_process.pid}")
            try:
                os.kill(self._cmd_process.pid, 0)
                self._cmd_process.terminate()
                try:
                    self._cmd_process.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
                    self._logger.debug(f"Subprocess {self._cmd_process.pid} terminated successfully")
                except Exception:
                    self._logger.warning(f"Subprocess {self._cmd_process.pid} did not terminate gracefully, killing")
                    with suppress(Exception):
                        self._cmd_process.kill()
            except OSError:
                self._logger.debug(f"Subprocess {self._cmd_process.pid} already exited")
                pass  # Process already exited

        # Step 2: Force terminate the ht process with SIGTERM, then SIGKILL if needed
        self._logger.debug(f"Force terminating ht process {self._ht_proc.pid}")

        # Try SIGTERM first
        try:
            self._ht_proc.terminate()
            self._logger.debug(f"Sent SIGTERM to ht process {self._ht_proc.pid}")
        except Exception as e:
            self._logger.debug(f"Failed to send SIGTERM to ht process {self._ht_proc.pid}: {e}")

        # Wait for termination
        start_time = time.time()
        while self._ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # SIGTERM timeout, try SIGKILL
                self._logger.warning(
                    f"ht process {self._ht_proc.pid} did not terminate with SIGTERM within timeout, sending SIGKILL"
                )
                try:
                    self._ht_proc.kill()
                    self._logger.debug(f"Sent SIGKILL to ht process {self._ht_proc.pid}")
                except Exception as e:
                    self._logger.debug(f"Failed to send SIGKILL to ht process {self._ht_proc.pid}: {e}")

                # Wait for SIGKILL to take effect
                kill_start_time = time.time()
                while self._ht_proc.poll() is None:
                    if time.time() - kill_start_time > timeout:
                        self._logger.error(f"ht process {self._ht_proc.pid} did not respond to SIGKILL within timeout")
                        break
                    time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
                break
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self._exit_code = self._ht_proc.returncode
        if self._exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        self._logger.debug(f"HTProcess exited via forced termination: exit_code={self._exit_code}")
        return self._exit_code

    def expect(self, pattern: str, timeout: float = DEFAULT_EXPECT_TIMEOUT) -> None:
        """
        Wait for a regex pattern to appear in the terminal output.

        This method efficiently waits for output by monitoring the output events from
        the ht process rather than polling with snapshots. It checks both the current
        terminal state (via snapshot) and any new output that arrives.

        Args:
            pattern: The regex pattern to look for in the terminal output
            timeout: Maximum time to wait in seconds (default: 5.0)

        Raises:
            TimeoutError: If the pattern doesn't appear within the timeout period
            RuntimeError: If the ht process has exited
        """
        if self._ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self._ht_proc.returncode}")

        self._logger.debug(f"Expecting regex pattern: '{pattern}'")

        # Compile the regex pattern
        try:
            regex = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        # First check current terminal state
        snapshot = self.snapshot()
        if regex.search(snapshot.text):
            self._logger.debug(f"Pattern '{pattern}' found immediately in current terminal state")
            return

        # Start time for timeout tracking
        start_time = time.time()

        # Process events until we find the pattern or timeout
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                self._logger.debug(f"Pattern '{pattern}' not found in terminal output after {timeout} seconds")
                raise TimeoutError(f"Pattern '{pattern}' not found within {timeout} seconds")

            try:
                # Wait for next event with a short timeout to allow checking the overall timeout
                event = self._event_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            # Process the event
            if event["type"] == "output":
                self._output_events.append(event)
                # Check if pattern appears in this output
                if "data" in event and "seq" in event["data"] and regex.search(event["data"]["seq"]):
                    self._logger.debug(f"Pattern '{pattern}' found in output event")
                    return
            elif event["type"] == "exitCode":
                # Put back in queue for reader thread to handle
                self._event_queue.put(event)
                # Don't raise here - the process might have exited after outputting what we want
            elif event["type"] == "snapshot":
                # If we get a snapshot event, check its content
                if "data" in event and "text" in event["data"] and regex.search(event["data"]["text"]):
                    self._logger.debug(f"Pattern '{pattern}' found in snapshot event")
                    return

            # Take a new snapshot periodically to catch any missed output
            if len(self._output_events) % 10 == 0:  # Every 10 events
                snapshot = self.snapshot()
                if regex.search(snapshot.text):
                    self._logger.debug(f"Pattern '{pattern}' found in periodic snapshot")
                    return

    def expect_absent(self, pattern: str, timeout: float = DEFAULT_EXPECT_TIMEOUT) -> None:
        """
        Wait for a regex pattern to disappear from the terminal output.

        This method efficiently waits for output changes by monitoring the output events
        from the ht process rather than polling with snapshots. It periodically checks
        the terminal state to verify the pattern is gone.

        Args:
            pattern: The regex pattern that should disappear from the terminal output
            timeout: Maximum time to wait in seconds (default: 5.0)

        Raises:
            TimeoutError: If the pattern doesn't disappear within the timeout period
            RuntimeError: If the ht process has exited
        """
        if self._ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self._ht_proc.returncode}")

        self._logger.debug(f"Expecting regex pattern to disappear: '{pattern}'")

        # Compile the regex pattern
        try:
            regex = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        # Start time for timeout tracking
        start_time = time.time()

        while True:
            # Take a snapshot to check current state
            snapshot = self.snapshot()
            if not regex.search(snapshot.text):
                self._logger.debug(f"Pattern '{pattern}' is now absent from terminal output")
                return

            # Check timeout
            if time.time() - start_time > timeout:
                self._logger.debug(f"Pattern '{pattern}' still present in terminal output after {timeout} seconds")
                raise TimeoutError(f"Pattern '{pattern}' still present after {timeout} seconds")

            # Wait for next event with a short timeout
            try:
                event = self._event_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            # Process the event
            if event["type"] == "output":
                self._output_events.append(event)
            elif event["type"] == "exitCode":
                # Put back in queue for reader thread to handle
                self._event_queue.put(event)
                # Don't raise here - the process might have exited after the pattern disappeared


@contextmanager
def terminal_session(
    command: Command,
    rows: Rows = None,
    cols: Cols = None,
    logger: Logger = None,
    extra_subscribes: ExtraSubscribes = None,
) -> Iterator[HtWrapper]:
    """
    The terminal_session context manager is a wrapper around `run` which ensures that the underlying process
    gets cleaned up:

    ```python
    with terminal_session("some command") as proc:
        # interact with the running command here
        assert proc.exit_code is not None
        s = proc.snapshot()

    # htty terminates your command on context exit
    assert proc.exit_code is None
    assert "hello world" in proc.snapshot()
    ```

    Its usage is otherwise the same as `run`.
    Like `run` it returns a `HtWrapper`.

    """

    proc = run(
        command,
        rows=rows,
        cols=cols,
        no_exit=True,
        logger=logger,
        extra_subscribes=extra_subscribes,
    )
    try:
        yield proc
    finally:
        try:
            if proc.cmd.pid:
                proc.cmd.terminate()
                proc.cmd.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception:
            try:
                if proc.cmd.pid:
                    proc.cmd.kill()
            except Exception:
                pass

        try:
            proc.ht.terminate()
            proc.ht.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception:
            with suppress(Exception):
                proc.ht.kill()


def run(
    command: Command,
    rows: Rows = None,
    cols: Cols = None,
    no_exit: NoExit = True,
    logger: Logger = None,
    extra_subscribes: ExtraSubscribes = None,
) -> HtWrapper:
    """
    As a user of the htty python library, your code will run in the python process at the root of this
    process tree:

        python '{/path/to/your/code.py}'
        └── ht
            └── sh -c '{modified command}'

    So if you're using htty to wrap vim, the process tree is:

    ```
    python
    └── ht
        └── sh
            └── vim
    ```

    This function invokes `ht` as a subprocess such that you end up with a process tree like the one shown
    above. It returns an `HtWrapper` object which can be used to interact with ht and its child process.

    It's up to you to clean up this process when you're done:

    ```python
    proc = run("some command")
    # do stuff
    proc.exit()
    ```

    If you'd rather not risk having a bunch of `ht` processes lying around and wasting CPU cycles,
    consider using the `terminal_session` instead.

    For reasons that are documented in
    [htty-core](https://matrixmanatyrservice.github.io/htty/htty-core/htty_core.html#HtEvent.COMMAND_COMPLETED), the
    command that ht runs is not:

        sh -c '{command}'

    Instead it's something like this:

        sh -c '{command} ; exit_code=$? ; /path/to/ht wait-exit /path/to/tmp/ht_fifo_5432 ; exit $exit_code'

    Because of this, it's possible to come up with command strings that cause sh to behave in problematic ways (for
    example: `'`). For now the mitigation for this is: "don't do that." (If you'd like me to prioritize changing this
    please leave a comment in https://github.com/MatrixManAtYrService/htty/issues/2)
    """
    # Use provided logger or fall back to default
    process_logger = logger or default_logger

    # Create a queue for events
    event_queue: queue.Queue[dict[str, Any]] = queue.Queue()

    # Build the ht subscription list
    base_subscribes = [
        HtEvent.INIT,
        HtEvent.SNAPSHOT,
        HtEvent.OUTPUT,
        HtEvent.RESIZE,
        HtEvent.PID,
        HtEvent.EXIT_CODE,
        HtEvent.COMMAND_COMPLETED,
    ]
    if extra_subscribes:
        # Convert string subscribes to HtEvent enum values
        for sub in extra_subscribes:
            try:
                base_subscribes.append(HtEvent(sub))
            except ValueError:
                process_logger.warning(f"Unknown subscription event: {sub}")

    # Convert command to string if it's a list, properly escaping shell arguments
    command_str = command if isinstance(command, str) else " ".join(shlex.quote(arg) for arg in command)

    # Create HtArgs and use htty_core.run()
    ht_args = HtArgs(
        command=command_str,  # Use the already-formatted command string
        subscribes=base_subscribes,
        rows=rows,
        cols=cols,
    )

    # Log the exact command that would be run
    cmd_args = ht_args.get_command()
    process_logger.debug(f"Launching command: {' '.join(cmd_args)}")

    ht_proc = htty_core_run(ht_args)

    process_logger.debug(f"ht started: PID {ht_proc.pid}")

    # Create a reader thread to capture ht output
    def reader_thread(
        ht_proc: subprocess.Popen[str],
        queue_obj: queue.Queue[dict[str, Any]],
        ht_process: HtWrapper,
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
                    ht_process.add_output_event(event)
                elif event["type"] == "exitCode":
                    thread_logger.debug(
                        f"ht process {ht_proc.pid} subprocess exited with code: {event.get('data', {}).get('exitCode')}"
                    )
                    ht_process.set_subprocess_exited(True)
                    exit_code = event.get("data", {}).get("exitCode")
                    if exit_code is not None:
                        ht_process.cmd.exit_code = exit_code
                elif event["type"] == "pid":
                    thread_logger.debug(f"ht process {ht_proc.pid} subprocess PID: {event.get('data', {}).get('pid')}")
                    pid = event.get("data", {}).get("pid")
                    if pid is not None:
                        ht_process.cmd.pid = pid
                elif event["type"] == "commandCompleted":
                    # Command has completed - this is the reliable signal that subprocess finished
                    ht_process.set_subprocess_completed(True)
                elif event["type"] == "debug":
                    thread_logger.debug(f"ht process {ht_proc.pid} debug: {event.get('data', {})}")
                    # Note: We no longer rely on debug events for subprocess_completed
                    # The commandCompleted event (above) is the reliable source
            except json.JSONDecodeError as e:
                # Only log raw stdout when we can't parse it as JSON - this indicates an unexpected message
                thread_logger.warning(f"ht process {ht_proc.pid} non-JSON stdout: {line} (error: {e})")
                pass

        thread_logger.debug(f"Reader thread exiting for ht process {ht_proc.pid}")

    # Create an HtWrapper instance
    process = HtWrapper(
        ht_proc,
        event_queue,
        command=command_str,
        rows=rows,
        cols=cols,
        no_exit=no_exit,
        logger=process_logger,
    )

    # Start the reader thread for stdout
    stdout_thread = threading.Thread(
        target=reader_thread,
        args=(ht_proc, event_queue, process, process_logger),
        daemon=True,
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
                process.cmd.pid = pid
                break
        except queue.Empty:
            continue

    time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
    return process
