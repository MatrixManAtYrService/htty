"""
Core htty-ht functionality for terminal automation.

This module provides the minimal interface for running ht processes.
"""

import os
import subprocess
import sysconfig
from typing import Optional, Union

# Python 3.11+ compatibility for StrEnum
try:
    from enum import StrEnum
except ImportError:
    # Fallback for Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        """String enumeration for Python < 3.11 compatibility."""
        pass

__all__ = [
    "HtEvent",
    "HtArgs",
    "find_ht_binary",
    "run",
]


class HtEvent(StrEnum):
    """Event types that can be subscribed to from the ht process."""

    INIT = "init"
    SNAPSHOT = "snapshot"
    OUTPUT = "output"
    RESIZE = "resize"
    PID = "pid"
    EXIT_CODE = "exitCode"
    COMMAND_COMPLETED = "commandCompleted"
    DEBUG = "debug"


class HtArgs:
    """Arguments for running an ht process."""

    def __init__(
        self,
        command: Union[str, list[str]],
        subscribes: Optional[list[HtEvent]] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
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
    """Run an ht process with the given arguments.

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
