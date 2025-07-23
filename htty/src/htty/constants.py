# Auto-generated constants from nix/lib/constants.nix
# DO NOT EDIT THE GENERATED SECTIONS MANUALLY

# [[[cog
# import os
# # Terminal configuration
# default_cols = int(os.environ['HTTY_DEFAULT_COLS'])
# default_rows = int(os.environ['HTTY_DEFAULT_ROWS'])
#
# # Timing constants (convert milliseconds to seconds for Python)
# default_sleep_after_keys = int(os.environ['HTTY_DEFAULT_SLEEP_AFTER_KEYS_MS']) / 1000.0
# subprocess_exit_detection_delay = int(os.environ['HTTY_SUBPROCESS_EXIT_DETECTION_DELAY_MS']) / 1000.0
# default_subprocess_wait_timeout = int(os.environ['HTTY_DEFAULT_SUBPROCESS_WAIT_TIMEOUT_MS']) / 1000.0
# default_snapshot_timeout = int(os.environ['HTTY_DEFAULT_SNAPSHOT_TIMEOUT_MS']) / 1000.0
# default_exit_timeout = int(os.environ['HTTY_DEFAULT_EXIT_TIMEOUT_MS']) / 1000.0
# default_graceful_termination_timeout = int(os.environ['HTTY_DEFAULT_GRACEFUL_TERMINATION_TIMEOUT_MS']) / 1000.0
# default_expect_timeout = int(os.environ['HTTY_DEFAULT_EXPECT_TIMEOUT_MS']) / 1000.0
# snapshot_retry_timeout = int(os.environ['HTTY_SNAPSHOT_RETRY_TIMEOUT_MS']) / 1000.0
#
# # Retry counts and thresholds
# max_snapshot_retries = int(os.environ['HTTY_MAX_SNAPSHOT_RETRIES'])
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

# Timing constants (in seconds for Python)
# [[[cog
# cog.outl(f"DEFAULT_SLEEP_AFTER_KEYS = {default_sleep_after_keys}")
# cog.outl(f"DEFAULT_SUBPROCESS_WAIT_TIMEOUT = {default_subprocess_wait_timeout}")
# cog.outl(f"DEFAULT_SNAPSHOT_TIMEOUT = {default_snapshot_timeout}")
# cog.outl(f"DEFAULT_EXIT_TIMEOUT = {default_exit_timeout}")
# cog.outl(f"DEFAULT_GRACEFUL_TERMINATION_TIMEOUT = {default_graceful_termination_timeout}")
# cog.outl(f"SNAPSHOT_RETRY_TIMEOUT = {snapshot_retry_timeout}")
# cog.outl(f"SUBPROCESS_EXIT_DETECTION_DELAY = {subprocess_exit_detection_delay}")
# cog.outl(f"DEFAULT_EXPECT_TIMEOUT = {default_expect_timeout}")
# ]]]
DEFAULT_SLEEP_AFTER_KEYS = 0.1
DEFAULT_SUBPROCESS_WAIT_TIMEOUT = 2.0
DEFAULT_SNAPSHOT_TIMEOUT = 5.0
DEFAULT_EXIT_TIMEOUT = 5.0
DEFAULT_GRACEFUL_TERMINATION_TIMEOUT = 5.0
SNAPSHOT_RETRY_TIMEOUT = 0.1
SUBPROCESS_EXIT_DETECTION_DELAY = 0.2
DEFAULT_EXPECT_TIMEOUT = 5.0
# [[[end]]]

# Retry counts and thresholds
# [[[cog
# cog.outl(f"MAX_SNAPSHOT_RETRIES = {max_snapshot_retries}")
# ]]]
MAX_SNAPSHOT_RETRIES = 10
# [[[end]]]

__all__ = [
    "DEFAULT_TERMINAL_COLS",
    "DEFAULT_TERMINAL_ROWS",
    "DEFAULT_SLEEP_AFTER_KEYS",
    "DEFAULT_SUBPROCESS_WAIT_TIMEOUT",
    "DEFAULT_SNAPSHOT_TIMEOUT",
    "DEFAULT_EXIT_TIMEOUT",
    "DEFAULT_GRACEFUL_TERMINATION_TIMEOUT",
    "SNAPSHOT_RETRY_TIMEOUT",
    "SUBPROCESS_EXIT_DETECTION_DELAY",
    "DEFAULT_EXPECT_TIMEOUT",
    "MAX_SNAPSHOT_RETRIES",
]
