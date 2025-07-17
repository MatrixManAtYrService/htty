# Auto-generated constants from nix/lib/constants.nix
# DO NOT EDIT THE GENERATED SECTIONS MANUALLY

# [[[cog
# import os
# # Terminal configuration
# default_cols = int(os.environ['HTTY_DEFAULT_COLS'])
# default_rows = int(os.environ['HTTY_DEFAULT_ROWS'])
# ]]]
# [[[end]]]

# Terminal configuration
# [[[cog
# cog.outl(f"DEFAULT_TERMINAL_COLS = {default_cols}")
# cog.outl(f"DEFAULT_TERMINAL_ROWS = {default_rows}")
# ]]]
DEFAULT_TERMINAL_COLS = 60
DEFAULT_TERMINAL_ROWS = 30
# [[[end]]]

__all__ = [
    "DEFAULT_TERMINAL_COLS",
    "DEFAULT_TERMINAL_ROWS",
]
