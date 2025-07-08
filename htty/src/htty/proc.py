"""
Process manipulation protocol and implementations for HTProcess wrapper.
"""

import os
import signal
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from subprocess import Popen

    from .ht import HtWrapper

DEFAULT_SLEEP_AFTER_KEYS = 0.1


class ProcessController(Protocol):
    """Protocol for process manipulation operations."""

    def exit(self, timeout: Optional[float] = None) -> int:
        """Exit the process."""
        ...

    def terminate(self) -> None:
        """Terminate the process."""
        ...

    def kill(self) -> None:
        """Force kill the process."""
        ...

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """Wait for the process to finish."""
        ...

    def poll(self) -> Optional[int]:
        """Check if the process is still running."""
        ...

    @property
    def pid(self) -> Optional[int]:
        """Get the process ID."""
        ...

    @pid.setter
    def pid(self, value: Optional[int]) -> None:
        """Set the process ID."""
        ...

    @property
    def exit_code(self) -> Optional[int]:
        """Get the exit code of the process."""
        ...

    @exit_code.setter
    def exit_code(self, value: Optional[int]) -> None:
        """Set the exit code of the process."""
        ...

    @property
    def completed(self) -> bool:
        """Check if the process has completed."""
        ...


class HtProcess(ProcessController):
    """Controller for the parent ht process."""

    def __init__(self, ht_proc: "Popen[str]", wrapper: Optional["HtWrapper"] = None):
        self._ht_proc = ht_proc
        self._wrapper = wrapper
        self._exit_code: Optional[int] = None
        self._pid: Optional[int] = ht_proc.pid

    def exit(self, timeout: Optional[float] = 5.0) -> int:
        """Exit the ht process."""
        if self._wrapper is not None:
            # Use the wrapper's sophisticated exit logic
            return self._wrapper.exit(timeout or 5.0)
        else:
            # Fallback to simple wait
            try:
                if timeout is None:
                    self._exit_code = self._ht_proc.wait()
                else:
                    self._exit_code = self._ht_proc.wait(timeout=timeout)
                return self._exit_code
            except Exception:
                return self._ht_proc.poll() or 0

    def terminate(self) -> None:
        """Terminate the ht process."""
        with suppress(Exception):
            self._ht_proc.terminate()

    def kill(self) -> None:
        """Force kill the ht process."""
        with suppress(Exception):
            self._ht_proc.kill()

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """Wait for the ht process to finish."""
        try:
            if timeout is None:
                self._exit_code = self._ht_proc.wait()
            else:
                self._exit_code = self._ht_proc.wait(timeout=timeout)
            return self._exit_code
        except Exception:
            return None

    def poll(self) -> Optional[int]:
        """Check if the ht process is still running."""
        return self._ht_proc.poll()

    @property
    def pid(self) -> Optional[int]:
        """Get the process ID."""
        return self._pid

    @pid.setter
    def pid(self, value: Optional[int]) -> None:
        """Set the process ID."""
        self._pid = value

    @property
    def exit_code(self) -> Optional[int]:
        """Get the exit code of the process."""
        return self._exit_code

    @exit_code.setter
    def exit_code(self, value: Optional[int]) -> None:
        """Set the exit code of the process."""
        self._exit_code = value

    @property
    def completed(self) -> bool:
        """Check if the process has completed."""
        return self._ht_proc.poll() is not None


class CmdProcess(ProcessController):
    """Controller for the subprocess being monitored by ht (merges SubprocessController functionality)."""

    def __init__(self, pid: Optional[int] = None):
        self._pid = pid
        self._exit_code: Optional[int] = None
        self._termination_initiated = False
        self._completed = False

    @property
    def pid(self) -> Optional[int]:
        """Get the process ID."""
        return self._pid

    @pid.setter
    def pid(self, value: Optional[int]) -> None:
        """Set the process ID."""
        self._pid = value

    @property
    def exit_code(self) -> Optional[int]:
        """Get the exit code of the subprocess."""
        return self._exit_code

    @exit_code.setter
    def exit_code(self, value: Optional[int]) -> None:
        """Set the exit code of the subprocess."""
        self._exit_code = value

    @property
    def completed(self) -> bool:
        """Check if the subprocess has completed."""
        return self._completed

    def set_completed(self, completed: bool) -> None:
        """Set the completion status (for internal use by wrapper)."""
        self._completed = completed

    def exit(self, timeout: Optional[float] = 5.0) -> int:
        """Exit the subprocess (same as wait for subprocesses)."""
        result = self.wait(timeout)
        return result if result is not None else 0

    def poll(self) -> Optional[int]:
        """Check if the subprocess is still running."""
        if self._pid is None:
            return self._exit_code
        try:
            os.kill(self._pid, 0)
            return None  # Process is still running
        except OSError:
            return self._exit_code  # Process has exited

    def terminate(self) -> None:
        """Terminate the subprocess."""
        if self._pid is None:
            raise RuntimeError("No subprocess PID available")
        with suppress(OSError):
            self._termination_initiated = True
            os.kill(self._pid, signal.SIGTERM)

    def kill(self) -> None:
        """Force kill the subprocess."""
        if self._pid is None:
            raise RuntimeError("No subprocess PID available")
        with suppress(OSError):
            self._termination_initiated = True
            os.kill(self._pid, signal.SIGKILL)

    def wait(self, timeout: Optional[float] = 5.0) -> Optional[int]:
        """
        Wait for the subprocess to finish.

        Args:
            timeout: Maximum time to wait (in seconds). Defaults to 5.0 seconds.

        Returns:
            The exit code of the subprocess, or None if timeout reached
        """
        if self._pid is None:
            raise RuntimeError("No subprocess PID available")

        start_time = time.time()
        while True:
            try:
                os.kill(self._pid, 0)  # Check if process is still running

                # Check timeout
                if timeout is not None and (time.time() - start_time) > timeout:
                    return None  # Timeout reached

                time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
            except OSError:
                # Process has exited
                # Try to get the actual exit code
                try:
                    pid_result, status = os.waitpid(self._pid, os.WNOHANG)
                    if pid_result == self._pid:
                        if os.WIFEXITED(status):
                            self._exit_code = os.WEXITSTATUS(status)
                        elif os.WIFSIGNALED(status):
                            signal_num = os.WTERMSIG(status)
                            self._exit_code = 128 + signal_num
                        else:
                            self._exit_code = 1
                    else:
                        # Process was already reaped, use stored exit code or default
                        if self._exit_code is None:
                            self._exit_code = 0 if not self._termination_initiated else 137
                except OSError:
                    # Couldn't get exit code, use reasonable default
                    if self._exit_code is None:
                        self._exit_code = 0 if not self._termination_initiated else 137

                return self._exit_code
