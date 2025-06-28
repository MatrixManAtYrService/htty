#!/usr/bin/env python3
"""
Entry point for htty CLI when run as python -m htty
"""

from .cli import htty_sync

if __name__ == "__main__":
    htty_sync()
