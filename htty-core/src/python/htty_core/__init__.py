"""
htty-core: A thin wrapper around a forked [ht](https://github.com/andyk/ht) binary for use with [htty](https://matrixmanatyrservice.github.io/htty/htty.html).
"""

from .core import Cols, Command, HtArgs, HtEvent, Rows, find_ht_binary, run

__all__ = ["HtArgs", "HtEvent", "find_ht_binary", "run", "Command", "Rows", "Cols", "__version__"]
# [[[cog
# import os
# cog.out(f'__version__ = "{os.environ["HTTY_VERSION"]}"')
# ]]]
__version__ = "0.2.28"
# [[[end]]]
