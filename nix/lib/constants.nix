# Centralized constants for htty project
{ pkgs, ... }:

{
  # Terminal configuration
  terminal = {
    # Referenced in: htty-core/src/rust/cli.rs (currently 120x40), htty/src/htty/cli.py (currently 20x50)
    # Used as: Default terminal dimensions when no size is specified
    default_cols = 60;
    default_rows = 30;
  };

  # Timing constants (all values in milliseconds for consistency)
  timing = {
    # Sleep and delay intervals

    # Referenced in: htty/src/htty/ht.py:192, htty/src/htty/cli.py:182, htty/src/htty/proc.py:16
    # Used as: Brief pause after sending keys to terminal to ensure they're processed
    default_sleep_after_keys_ms = 100;

    # Referenced in: htty/src/htty/ht.py:48, used in _forced_exit() method
    # Used as: Delay to detect if subprocess has exited before attempting forced termination
    subprocess_exit_detection_delay_ms = 200;

    # Referenced in: htty-core/src/rust/main.rs:173,198, htty-core/src/rust/pty.rs:104
    # Used as: Delay for coordination between processes and channel emptiness checks
    coordination_delay_ms = 200;

    # Referenced in: htty-core/src/rust/pty.rs:148, multiple ht.py timeout contexts
    # Used as: General short sleep interval for polling loops and heartbeat checks
    general_sleep_interval_ms = 100;

    # Timeout values

    # Referenced in: htty/src/htty/ht.py:43, used in process termination methods
    # Used as: Maximum time to wait for subprocess termination during cleanup
    default_subprocess_wait_timeout_ms = 2000;

    # Referenced in: htty/src/htty/ht.py:44, used in snapshot() method
    # Used as: Maximum time to wait for terminal snapshot to complete
    default_snapshot_timeout_ms = 5000;

    # Referenced in: htty/src/htty/ht.py:45, htty/src/htty/cli.py:232, used in exit() method
    # Used as: Maximum time to wait for graceful process exit before forcing termination
    default_exit_timeout_ms = 5000;

    # Referenced in: htty/src/htty/ht.py:46, used in _graceful_exit() method
    # Used as: Maximum time to wait during graceful termination sequence
    default_graceful_termination_timeout_ms = 5000;

    # Referenced in: htty/src/htty/ht.py:50, used in expect() and expect_absent() methods
    # Used as: Default timeout for waiting for patterns to appear/disappear in terminal output
    default_expect_timeout_ms = 5000;

    # Referenced in: htty/src/htty/ht.py:47, used in snapshot() retry logic
    # Used as: Time between snapshot retry attempts when first attempt fails
    snapshot_retry_timeout_ms = 500;

    # Referenced in: htty-core/src/rust/session.rs:169 (as Duration::from_secs(5))
    # Used as: Maximum time to wait for subscription acknowledgment from ht process
    subscription_timeout_ms = 5000;

    # Monitoring intervals

    # Referenced in: htty-core/src/rust/main.rs:131
    # Used as: Frequency to check if channels are empty during process coordination
    emptiness_check_interval_ms = 10;

    # Referenced in: htty-core/src/rust/pty.rs:74
    # Used as: Polling interval for FIFO monitoring in PTY management
    fifo_monitoring_interval_ms = 50;

    # Referenced in: htty-core/src/rust/pty.rs:134 (as Duration::from_secs(60))
    # Used as: Interval for PTY heartbeat to keep connection alive
    pty_heartbeat_interval_ms = 60000; # 60 seconds

    # Referenced in: htty-core/src/rust/pty.rs:148
    # Used as: Delay between heartbeat checks in PTY management loop
    heartbeat_check_delay_ms = 100;

    # Referenced in: htty-core/src/rust/api/stdio.rs:54
    # Used as: Delay when checking command channel for new messages
    command_channel_check_delay_ms = 100;
  };

  # Buffer sizes and limits
  buffers = {
    # Referenced in: htty-core/src/rust/pty.rs:162 (as const READ_BUF_SIZE: usize = 128 * 1024)
    # Used as: Size of buffer for reading PTY output, affects performance and memory usage
    read_buf_size = 131072; # 128 * 1024

    # Referenced in: htty-core/src/rust/main.rs:30, htty-core/src/rust/session.rs (multiple channels)
    # Used as: Buffer size for mpsc channels carrying events and data between threads
    channel_buffer_size = 1024;

    # Referenced in: htty-core/src/rust/main.rs (multiple single-slot channels)
    # Used as: Buffer size for synchronization channels that only need one slot
    single_slot_channel_size = 1;

    # Referenced in: htty-core/src/rust/session.rs:39 (broadcast::channel(1024))
    # Used as: Buffer size for broadcast channels distributing events to multiple subscribers
    broadcast_channel_size = 1024;
  };

  # Retry counts and thresholds
  limits = {
    # Referenced in: htty/src/htty/ht.py:49, used in snapshot() method retry loop
    # Used as: Maximum number of attempts to retrieve a snapshot before giving up
    max_snapshot_retries = 10;
  };
}
