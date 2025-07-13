// Auto-generated constants from nix/lib/constants.nix
// DO NOT EDIT THE GENERATED SECTIONS MANUALLY

//[[[cog
// import os
// # Terminal configuration
// default_cols = int(os.environ['HTTY_DEFAULT_COLS'])
// default_rows = int(os.environ['HTTY_DEFAULT_ROWS'])
//
// # Timing constants (milliseconds)
// default_sleep_after_keys_ms = int(os.environ['HTTY_DEFAULT_SLEEP_AFTER_KEYS_MS'])
// subprocess_exit_detection_delay_ms = int(os.environ['HTTY_SUBPROCESS_EXIT_DETECTION_DELAY_MS'])
// coordination_delay_ms = int(os.environ['HTTY_COORDINATION_DELAY_MS'])
// general_sleep_interval_ms = int(os.environ['HTTY_GENERAL_SLEEP_INTERVAL_MS'])
// default_subprocess_wait_timeout_ms = int(os.environ['HTTY_DEFAULT_SUBPROCESS_WAIT_TIMEOUT_MS'])
// default_snapshot_timeout_ms = int(os.environ['HTTY_DEFAULT_SNAPSHOT_TIMEOUT_MS'])
// default_exit_timeout_ms = int(os.environ['HTTY_DEFAULT_EXIT_TIMEOUT_MS'])
// default_graceful_termination_timeout_ms = int(os.environ['HTTY_DEFAULT_GRACEFUL_TERMINATION_TIMEOUT_MS'])
// default_expect_timeout_ms = int(os.environ['HTTY_DEFAULT_EXPECT_TIMEOUT_MS'])
// snapshot_retry_timeout_ms = int(os.environ['HTTY_SNAPSHOT_RETRY_TIMEOUT_MS'])
// subscription_timeout_ms = int(os.environ['HTTY_SUBSCRIPTION_TIMEOUT_MS'])
// emptiness_check_interval_ms = int(os.environ['HTTY_EMPTINESS_CHECK_INTERVAL_MS'])
// fifo_monitoring_interval_ms = int(os.environ['HTTY_FIFO_MONITORING_INTERVAL_MS'])
// pty_heartbeat_interval_ms = int(os.environ['HTTY_PTY_HEARTBEAT_INTERVAL_MS'])
// heartbeat_check_delay_ms = int(os.environ['HTTY_HEARTBEAT_CHECK_DELAY_MS'])
// command_channel_check_delay_ms = int(os.environ['HTTY_COMMAND_CHANNEL_CHECK_DELAY_MS'])
//
// # Buffer sizes and limits
// read_buf_size = int(os.environ['HTTY_READ_BUF_SIZE'])
// channel_buffer_size = int(os.environ['HTTY_CHANNEL_BUFFER_SIZE'])
// single_slot_channel_size = int(os.environ['HTTY_SINGLE_SLOT_CHANNEL_SIZE'])
// broadcast_channel_size = int(os.environ['HTTY_BROADCAST_CHANNEL_SIZE'])
//
// # Retry counts and thresholds
// max_snapshot_retries = int(os.environ['HTTY_MAX_SNAPSHOT_RETRIES'])
//]]]
//[[[end]]]

use std::time::Duration;

// Terminal configuration
/*[[[cog
cog.outl(f"pub const DEFAULT_TERMINAL_COLS: u16 = {default_cols};")
cog.outl(f"pub const DEFAULT_TERMINAL_ROWS: u16 = {default_rows};")
]]]*/
pub const DEFAULT_TERMINAL_COLS: u16 = 60;
pub const DEFAULT_TERMINAL_ROWS: u16 = 30;
//[[[end]]]

// Timing constants as Duration values
/*[[[cog
cog.outl(f"pub const DEFAULT_SLEEP_AFTER_KEYS: Duration = Duration::from_millis({default_sleep_after_keys_ms});")
cog.outl(f"pub const SUBPROCESS_EXIT_DETECTION_DELAY: Duration = Duration::from_millis({subprocess_exit_detection_delay_ms});")
cog.outl(f"pub const COORDINATION_DELAY: Duration = Duration::from_millis({coordination_delay_ms});")
cog.outl(f"pub const GENERAL_SLEEP_INTERVAL: Duration = Duration::from_millis({general_sleep_interval_ms});")
cog.outl(f"pub const DEFAULT_SUBPROCESS_WAIT_TIMEOUT: Duration = Duration::from_millis({default_subprocess_wait_timeout_ms});")
cog.outl(f"pub const DEFAULT_SNAPSHOT_TIMEOUT: Duration = Duration::from_millis({default_snapshot_timeout_ms});")
cog.outl(f"pub const DEFAULT_EXIT_TIMEOUT: Duration = Duration::from_millis({default_exit_timeout_ms});")
cog.outl(f"pub const DEFAULT_GRACEFUL_TERMINATION_TIMEOUT: Duration = Duration::from_millis({default_graceful_termination_timeout_ms});")
cog.outl(f"pub const DEFAULT_EXPECT_TIMEOUT: Duration = Duration::from_millis({default_expect_timeout_ms});")
cog.outl(f"pub const SNAPSHOT_RETRY_TIMEOUT: Duration = Duration::from_millis({snapshot_retry_timeout_ms});")
cog.outl(f"pub const SUBSCRIPTION_TIMEOUT: Duration = Duration::from_millis({subscription_timeout_ms});")
cog.outl(f"pub const EMPTINESS_CHECK_INTERVAL: Duration = Duration::from_millis({emptiness_check_interval_ms});")
cog.outl(f"pub const FIFO_MONITORING_INTERVAL: Duration = Duration::from_millis({fifo_monitoring_interval_ms});")
cog.outl(f"pub const PTY_HEARTBEAT_INTERVAL: Duration = Duration::from_millis({pty_heartbeat_interval_ms});")
cog.outl(f"pub const HEARTBEAT_CHECK_DELAY: Duration = Duration::from_millis({heartbeat_check_delay_ms});")
cog.outl(f"pub const COMMAND_CHANNEL_CHECK_DELAY: Duration = Duration::from_millis({command_channel_check_delay_ms});")
]]]*/
pub const DEFAULT_SLEEP_AFTER_KEYS: Duration = Duration::from_millis(100);
pub const SUBPROCESS_EXIT_DETECTION_DELAY: Duration = Duration::from_millis(200);
pub const COORDINATION_DELAY: Duration = Duration::from_millis(200);
pub const GENERAL_SLEEP_INTERVAL: Duration = Duration::from_millis(100);
pub const DEFAULT_SUBPROCESS_WAIT_TIMEOUT: Duration = Duration::from_millis(2000);
pub const DEFAULT_SNAPSHOT_TIMEOUT: Duration = Duration::from_millis(5000);
pub const DEFAULT_EXIT_TIMEOUT: Duration = Duration::from_millis(5000);
pub const DEFAULT_GRACEFUL_TERMINATION_TIMEOUT: Duration = Duration::from_millis(5000);
pub const DEFAULT_EXPECT_TIMEOUT: Duration = Duration::from_millis(5000);
pub const SNAPSHOT_RETRY_TIMEOUT: Duration = Duration::from_millis(500);
pub const SUBSCRIPTION_TIMEOUT: Duration = Duration::from_millis(5000);
pub const EMPTINESS_CHECK_INTERVAL: Duration = Duration::from_millis(10);
pub const FIFO_MONITORING_INTERVAL: Duration = Duration::from_millis(50);
pub const PTY_HEARTBEAT_INTERVAL: Duration = Duration::from_millis(60000);
pub const HEARTBEAT_CHECK_DELAY: Duration = Duration::from_millis(100);
pub const COMMAND_CHANNEL_CHECK_DELAY: Duration = Duration::from_millis(100);
//[[[end]]]

// Buffer sizes and limits
/*[[[cog
cog.outl(f"pub const READ_BUF_SIZE: usize = {read_buf_size};")
cog.outl(f"pub const CHANNEL_BUFFER_SIZE: usize = {channel_buffer_size};")
cog.outl(f"pub const SINGLE_SLOT_CHANNEL_SIZE: usize = {single_slot_channel_size};")
cog.outl(f"pub const BROADCAST_CHANNEL_SIZE: usize = {broadcast_channel_size};")
]]]*/
pub const READ_BUF_SIZE: usize = 131072;
pub const CHANNEL_BUFFER_SIZE: usize = 1024;
pub const SINGLE_SLOT_CHANNEL_SIZE: usize = 1;
pub const BROADCAST_CHANNEL_SIZE: usize = 1024;
//[[[end]]]

// Retry counts and thresholds
/*[[[cog
cog.outl(f"pub const MAX_SNAPSHOT_RETRIES: usize = {max_snapshot_retries};")
]]]*/
pub const MAX_SNAPSHOT_RETRIES: usize = 10;
//[[[end]]]