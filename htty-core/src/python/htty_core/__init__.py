"""
htty-core: Core headless terminal functionality with bundled ht binary.

This package provides the core HTProcess class and handles finding the bundled ht binary.
"""

from .core import HTProcess, create_process, find_ht_binary

__all__ = ["HTProcess", "create_process", "find_ht_binary"]
__version__ = "0.3.0"
