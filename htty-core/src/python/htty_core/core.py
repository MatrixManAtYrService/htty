"""
Core htty-ht functionality for terminal automation.

This module provides the minimal interface for running ht processes.
"""

import os
import subprocess
import sysconfig
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Union

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


@dataclass
class HtArgs:
    """Arguments for running an ht process."""

    command: Union[str, list[str]]
    subscribes: list[HtEvent]
    rows: Optional[int] = None
    cols: Optional[int] = None

    def __post_init__(self):
        """Validate arguments after initialization."""
        if not self.command:
            raise ValueError("command cannot be empty")
        if not self.subscribes:
            raise ValueError("subscribes cannot be empty")
        if self.rows is not None and self.rows <= 0:
            raise ValueError("rows must be positive")
        if self.cols is not None and self.cols <= 0:
            raise ValueError("cols must be positive")
        if (self.rows is None) != (self.cols is None):
            raise ValueError("both rows and cols must be specified together, or neither")


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
    ht_binary = find_ht_binary()

    # Build command arguments
    cmd_args = [ht_binary]

    # Add subscription arguments
    if args.subscribes:
        subscribe_strings = [event.value for event in args.subscribes]
        cmd_args.extend(["--subscribe", ",".join(subscribe_strings)])

    # Add size arguments if specified
    if args.rows is not None and args.cols is not None:
        cmd_args.extend(["--size", f"{args.cols}x{args.rows}"])

    # Add separator and the command to run
    cmd_args.append("--")
    if isinstance(args.command, str):
        cmd_args.extend(args.command.split())
    else:
        cmd_args.extend(args.command)

    # Start the process
    return subprocess.Popen(
        cmd_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
