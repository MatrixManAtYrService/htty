"""
htty - Headless Terminal Python Library

A Python library for terminal automation, providing both synchronous CLI tools
and asynchronous library access for subprocess interaction.

This is a fork of ht with enhanced Python integration and reliable subprocess management.
"""

from ._find_ht import find_ht_bin
from .core import (
    HTProcess,
    SnapshotResult,
    SubprocessController,
    get_ht_help,
    run,
    terminal_session,
)
from .keys import (
    KeyInput,
    Press,
    key_to_string,
    keys_to_strings,
)

__all__ = [
    "HTProcess",
    "SnapshotResult",
    "Press",
    "KeyInput",
    "run",
    "terminal_session",
    "get_ht_help",
    "find_ht_bin",
    "SubprocessController",
    "key_to_string",
    "keys_to_strings",
]

__version__ = "0.3.0"
