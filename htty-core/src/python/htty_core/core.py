import os
import subprocess
import sys
import sysconfig
from typing import Annotated, Optional, Union

if sys.version_info >= (3, 11):
    # Python 3.11+ compatibility for StrEnum
    from enum import StrEnum
else:
    # Fallback for Python 3.10
    from enum import Enum

    class StrEnum(str, Enum):
        pass


# Import constants for type alias annotations
from .constants import DEFAULT_TERMINAL_COLS, DEFAULT_TERMINAL_ROWS

# Type aliases for common parameters
Command = Annotated[Union[str, list[str]], "run this command (as a subprocess of ht)"]
Rows = Annotated[
    Optional[int],
    f"number of rows for the headless terminal (default: {DEFAULT_TERMINAL_ROWS})",
]
Cols = Annotated[
    Optional[int],
    f"number of columns for the headless terminal (default: {DEFAULT_TERMINAL_COLS})",
]


__all__ = [
    "HtEvent",
    "HtArgs",
    "find_ht_binary",
    "run",
    "Command",
    "Rows",
    "Cols",
]


class HtEvent(StrEnum):
    """
    Event types that can be subscribed to from the ht process.

    The original set of events is documented [in the ht repo](https://github.com/andyk/ht?tab=readme-ov-file#events).

    Events added by `htty`:

    - pid
    - exitCode
    - debug
    - completed
    """

    INIT = "init"
    """
    Same as snapshot event (see below) but sent only once, as the first event after ht's start (when sent to
    STDOUT) and upon establishing of WebSocket connection.
    """

    SNAPSHOT = "snapshot"
    """
    Terminal window snapshot. Sent when the terminal snapshot is taken with the takeSnapshot command.

    Event data is an object with the following fields:

    - cols - current terminal width, number of columns
    - rows - current terminal height, number of rows
    - text - plain text snapshot as multi-line string, where each line represents a terminal row
    - seq - a raw sequence of characters, which when printed to a blank terminal puts it in the same state as
      ht's virtual terminal
    """

    OUTPUT = "output"
    """
    Terminal output. Sent when an application (e.g. shell) running under ht prints something to the terminal.

    Event data is an object with the following fields:

    - seq - a raw sequence of characters written to a terminal, potentially including control sequences
      (colors, cursor positioning, etc.)
    """

    RESIZE = "resize"
    """
    Terminal resize. Send when the terminal is resized with the resize command.

    Event data is an object with the following fields:

    - cols - current terminal width, number of columns
    - rows - current terminal height, number of rows
    """

    PID = "pid"
    """
    ht runs the indicated command in `sh`.
    This event provides the pid of that `sh` process
    """

    EXIT_CODE = "exitCode"
    """
    htty modified ht to stay open even after the command has completed.
    This event indicates the exit code of the underlying command.
    """

    COMMAND_COMPLETED = "commandCompleted"
    """
    htty modified ht to run your command like so:

    Previously, ht did the simple thing and ran your command like this:
    ```
    sh -c '{command}''
    ```

    Sometimes, the PTY would shut down before all output was processed by ht, causing snapshots taken
    after exit to be incomplete.
    To fix this htty modified ht to run your like so:

    ```
    sh -c '{command} ; exit_code=$? ; /path/to/ht wait-exit /path/to/a/temp/fifo ; exit $exit_code'
    ```

    (The fifo is used to notify `ht wait-exit` that it's safe to exit)

    Following this change, the command might complete at one time, and the exit code would be made available later.
    This event indicates when the command completed, exitCode appears when the shell exits.
    """

    DEBUG = "debug"
    """
    These events contain messages that might be helpful for debugging `ht`.
    """


class HtArgs:
    """
    The caller provides one of these when they want an `ht` process.
    """

    def __init__(
        self,
        command: Command,
        subscribes: Optional[list[HtEvent]] = None,
        rows: Rows = None,
        cols: Cols = None,
    ) -> None:
        self.command = command
        self.subscribes = subscribes or []
        self.rows = rows
        self.cols = cols

    def get_command(self, ht_binary: Optional[str] = None) -> list[str]:
        """Build the command line arguments for running ht.

        Args:
            ht_binary: Optional path to ht binary. If not provided, find_ht_binary() will be called.

        Returns:
            List of command arguments that would be passed to subprocess.Popen
        """
        if ht_binary is None:
            ht_binary = find_ht_binary()

        cmd_args = [ht_binary]

        # Add subscription arguments
        if self.subscribes:
            subscribe_strings = [event.value for event in self.subscribes]
            cmd_args.extend(["--subscribe", ",".join(subscribe_strings)])

        # Add size arguments if specified
        if self.rows is not None and self.cols is not None:
            cmd_args.extend(["--size", f"{self.cols}x{self.rows}"])

        # Add separator and the command to run
        cmd_args.append("--")
        if isinstance(self.command, str):
            cmd_args.extend(self.command.split())
        else:
            cmd_args.extend(self.command)

        return cmd_args


def find_ht_binary() -> str:
    """Find the bundled ht binary."""
    # Check HTTY_HT_BIN environment variable first
    env_path = os.environ.get("HTTY_HT_BIN")
    if env_path and os.path.isfile(env_path):
        return env_path

    ht_exe = "ht" + (sysconfig.get_config_var("EXE") or "")

    # First, try to find the binary relative to this package installation
    pkg_file = __file__  # This file: .../site-packages/htty_core/core.py
    pkg_dir = os.path.dirname(pkg_file)  # .../site-packages/htty_core/
    site_packages = os.path.dirname(pkg_dir)  # .../site-packages/
    python_env = os.path.dirname(site_packages)  # .../lib/python3.x/
    env_root = os.path.dirname(python_env)  # .../lib/
    actual_env_root = os.path.dirname(env_root)  # The actual environment root

    # Look for binary in the environment's bin directory
    env_bin_path = os.path.join(actual_env_root, "bin", ht_exe)
    if os.path.isfile(env_bin_path):
        return env_bin_path

    # Only look for the bundled binary - no system fallbacks
    raise FileNotFoundError(
        f"Bundled ht binary not found at expected location: {env_bin_path}. "
        f"This indicates a packaging issue with htty-core."
    )


def run(args: HtArgs) -> subprocess.Popen[str]:
    """
    Given some `HtArgs` object, run its command via ht.

    `ht` connect


    Returns a subprocess.Popen object representing the running ht process.
    The caller is responsible for managing the process lifecycle.
    """
    cmd_args = args.get_command()

    # Start the process
    return subprocess.Popen(
        cmd_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
