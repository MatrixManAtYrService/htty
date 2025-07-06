"""
htty-core: Core headless terminal functionality with bundled ht binary.

This package provides the minimal interface for running ht processes.
"""

from .core import HtArgs, HtEvent, find_ht_binary, run

__all__ = ["HtArgs", "HtEvent", "find_ht_binary", "run"]
__version__ = "0.3.0"
