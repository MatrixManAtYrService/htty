"""
htty-core: Core headless terminal functionality with bundled ht binary.

This package provides the minimal interface for running ht processes.
"""

from .constants import DEFAULT_TERMINAL_COLS, DEFAULT_TERMINAL_ROWS
from .core import HtArgs, HtEvent, find_ht_binary, run, Command, Rows, Cols

__all__ = [
    "HtArgs",
    "HtEvent",
    "find_ht_binary",
    "run",
    "Command",
    "Rows",
    "Cols",
    "DEFAULT_TERMINAL_COLS",
    "DEFAULT_TERMINAL_ROWS",
    "__version__"
]
# [[[cog
# import os
# cog.out(f'__version__ = "{os.environ["HTTY_VERSION"]}"')
# ]]]
__version__ = "0.2.25"
# [[[end]]]
