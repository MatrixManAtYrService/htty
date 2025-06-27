# Process Coordination in htty

## Overview

The htty system coordinates between multiple processes and tasks to provide reliable terminal automation while ensuring no data loss and supporting both graceful and forced shutdown strategies. This document describes the complete coordination pattern.

## The Original Problem

Before this implementation, there was a **deadlock** in the shutdown sequence:

1. **PTY Output Capture** waited for PTY EOF to complete
2. **Wait-Exit Process** waited for "exit" signal to be written to FIFO
3. **"Exit" Signal** was only written after PTY output capture completed
4. **PTY EOF** never occurred because wait-exit kept the PTY open

**Result**: `subprocess_controller.wait()` timed out after 5 seconds → subprocess killed with SIGKILL → exit code 137

## Architecture Components

### 1. **Subprocess Shell Command**
```bash
{original_command} ; exit_code=$? ; {ht_binary} wait-exit {fifo_path} ; exit $exit_code
```
- Runs the user's command
- Captures exit code
- Runs `wait-exit` to block on FIFO
- Preserves original exit code

### 2. **Wait-Exit Process** (`src/rust/main.rs:handle_waitexit`)
```rust
// Creates FIFO and blocks reading from it
let fifo_path_cstr = std::ffi::CString::new(fifo_path_str.as_bytes()).unwrap();
unsafe { libc::mkfifo(fifo_path_cstr.as_ptr(), 0o600); }

// Blocks until "exit" is written to FIFO
for line in reader.lines() {
    if line.trim() == "exit" { break; }
}
```

### 3. **FIFO Monitoring Task** (`src/rust/pty.rs`)
```rust
// Checks every 50ms for FIFO existence
let mut interval = tokio::time::interval(Duration::from_millis(50));
loop {
    interval.tick().await;
    if fifo_path_clone.exists() {
        // FIFO created = subprocess completed, send CommandCompleted event
        let _ = fifo_command_tx.try_send(Command::CommandCompleted(fifo_path_clone.clone()));
        break;
    }
}
```

### 4. **Command Channel Emptiness Tracker** (`src/rust/main.rs`)
```rust
// Tracks when command channel has been continuously empty
let mut last_command_time = std::time::Instant::now();
let mut emptiness_check_interval = tokio::time::interval(Duration::from_millis(10));

// Updates on every command received
command = command_rx.recv() => {
    last_command_time = std::time::Instant::now(); // Reset timer
    // ... handle command
}

// Checks every 10ms for 200ms of continuous emptiness
_ = emptiness_check_interval.tick() => {
    if let Some(fifo_path) = &pending_waitexit {
        let emptiness_duration = last_command_time.elapsed();
        if emptiness_duration >= Duration::from_millis(200) {
            // Signal wait-exit to complete
            writeln!(file, "exit");
        }
    }
}
```

### 5. **PTY Keep-Alive Task** (`src/rust/pty.rs`)
```rust
// Keeps ht process alive for snapshots after subprocess completion
let mut heartbeat_interval = tokio::time::interval(Duration::from_secs(60));
loop {
    tokio::select! {
        _ = heartbeat_interval.tick() => {
            if command_tx.try_send(Command::Debug("ptyHeartbeat".to_string())).is_err() {
                break; // Main process shutting down
            }
        }
        _ = tokio::time::sleep(Duration::from_millis(100)) => {
            if command_tx.is_closed() { break; }
        }
    }
}
```

### 6. **Intelligent Exit Strategy** (`src/python/htty/core.py`)
```python
def exit(self, timeout: float) -> int:
    if self.subprocess_exited:  # exitCode event received
        return self._graceful_exit(timeout)  # Send exit command
    else:
        return self._forced_exit(timeout)    # SIGTERM then SIGKILL
```

## Event Flow Sequence

### Normal Execution Flow

```
1. User Command Starts
   ├─ Subprocess launched with wait-exit wrapper
   ├─ FIFO monitoring task starts (50ms interval)
   ├─ PTY output capture begins
   └─ Command channel emptiness tracking starts (10ms interval)

2. User Interactions
   ├─ send_keys() → updates last_command_time
   ├─ snapshot() → updates last_command_time  
   └─ All commands reset the 200ms emptiness timer

3. Subprocess Completion
   ├─ Original command finishes
   ├─ wait-exit process starts and creates FIFO
   ├─ FIFO monitoring detects FIFO → CommandCompleted event
   ├─ CommandCompleted handler sets pending_waitexit = Some(fifo_path)
   └─ exitCode event emitted by subprocess completion

4. Quiescence Detection (200ms of no commands)
   ├─ Emptiness timer reaches 200ms
   ├─ "exit" written to FIFO
   ├─ wait-exit process completes
   ├─ Subprocess exits with preserved exit code
   └─ PTY task continues running (keeps ht alive for snapshots)

5. User Calls exit()
   ├─ subprocess_exited == True (exitCode received)
   ├─ Graceful shutdown: send exit command to ht
   ├─ PTY task detects channel closure and exits
   └─ ht process exits gracefully with code 0
```

### Alternative: Forced Exit Flow

```
5. User Calls exit() (while subprocess still running)
   ├─ subprocess_exited == False
   ├─ Wait 500ms for any pending exitCode event
   ├─ Still no exitCode → forced termination
   ├─ SIGTERM subprocess → SIGTERM ht process
   └─ ht process exits with code -15 (expected for forced termination)
```

## Timing and Delays

### Critical Timing Parameters

| Parameter | Value | Purpose | Location |
|-----------|--------|---------|----------|
| **FIFO Check Interval** | 50ms | Detect subprocess completion | `src/rust/pty.rs` |
| **Emptiness Check Interval** | 10ms | Monitor command channel | `src/rust/main.rs` |
| **Quiescence Period** | 200ms | Ensure no pending commands | `src/rust/main.rs` |
| **Brief Exit Wait** | 500ms | Allow pending exitCode events | `src/python/htty/core.py` |
| **PTY Heartbeat** | 60s | Keep-alive signal | `src/rust/pty.rs` |

### Why 200ms Quiescence?

The 200ms delay ensures that all commands working their way through the system have been processed:

- **JSON Parsing**: Commands from stdin are parsed
- **Channel Transit**: Commands move through tokio mpsc channels  
- **Event Processing**: Commands are handled by the main event loop
- **PTY Operations**: Any final PTY reads/writes complete

This is **much safer** than the original approach which only waited for PTY EOF.

### Why 500ms Brief Wait?

When `exit()` is called, we briefly wait for any `exitCode` event that might be in transit:

- Network delays (if using HTTP API)
- Event queue processing delays  
- Race conditions between `exit()` call and subprocess completion

## Data Protection Guarantees

### 1. **No PTY Data Loss**
- PTY output capture completes **before** signaling wait-exit
- 200ms quiescence ensures all output is processed
- PTY task stays alive to keep channels open

### 2. **No Command Loss**  
- Command channel emptiness ensures all user commands processed
- Brief wait period catches race conditions
- Commands sent during quiescence period restart the timer

### 3. **Exit Code Preservation**
- Original subprocess exit code captured before wait-exit
- Shell wrapper: `exit_code=$? ; wait-exit ; exit $exit_code`
- `exitCode` event reliably delivered to Python layer

### 4. **Snapshot Availability**
- ht process stays alive after subprocess completion
- VT (terminal state) preserved in memory
- PTY task keeps running until explicit exit

## Exit Strategy Decision Tree

```
ht.exit() called
├─ subprocess_exited == True?
│  ├─ Yes → Graceful Exit
│  │  ├─ Send {"type": "exit"} command
│  │  ├─ ht process shuts down cleanly
│  │  └─ Return exit_code = 0
│  └─ No → Check for pending exitCode
│     ├─ Wait 500ms for exitCode event
│     ├─ exitCode received? → Graceful Exit
│     └─ Still no exitCode → Forced Exit
│        ├─ SIGTERM subprocess
│        ├─ SIGTERM ht process  
│        ├─ Wait timeout → SIGKILL ht process
│        └─ Return exit_code = -15 (expected)
```

## Edge Cases and Handling

### 1. **Rapid Command Sequences**
- **Problem**: User sends commands in quick succession
- **Solution**: Each command resets the 200ms timer
- **Result**: wait-exit only signaled after true quiescence

### 2. **Network Delays (HTTP API)**
- **Problem**: Commands may be buffered in network/HTTP layers
- **Solution**: 200ms is sufficient for typical network delays
- **Fallback**: Brief wait period in `exit()` handles remaining races

### 3. **Very Fast Subprocess Completion**
- **Problem**: Subprocess completes before user interactions finish
- **Solution**: FIFO monitoring + quiescence ensures proper ordering
- **Result**: No premature signaling even for instant commands

### 4. **Exit During Active Subprocess**
- **Problem**: User calls `exit()` while subprocess waiting for input
- **Solution**: Forced termination path with proper signal escalation
- **Result**: Clean forced shutdown with expected exit codes

### 5. **Multiple Exit Calls**
- **Problem**: User calls `exit()` multiple times
- **Solution**: First call handles cleanup, subsequent calls are no-ops
- **Result**: Consistent behavior regardless of usage pattern

## Debug Event Sequence

For troubleshooting, the system emits debug events showing the coordination:

```
startingFifoMonitoring          # FIFO monitoring task started
commandCompletedReceived        # CommandCompleted event processed  
signalingWaitexit              # About to write "exit" to FIFO
exitSignalSent                 # Successfully wrote "exit" to FIFO
outputCaptureComplete          # PTY output capture finished
coordinationComplete           # Wait coordination finished  
ptyContinuingForSnapshots      # PTY task staying alive
ptyHeartbeat                   # Periodic keep-alive (every 60s)
ptyTaskExiting                 # PTY task shutting down gracefully
```

## Performance Characteristics

### Latency (subprocess completion → exit code available)
- **Typical**: ~250ms (50ms detection + 200ms quiescence)
- **Fast commands**: Same (quiescence period dominates)
- **Slow commands**: Same (detection happens at completion)

### Resource Usage
- **CPU**: Minimal (50ms + 10ms intervals are very light)
- **Memory**: Constant (no accumulation, bounded queues)
- **File Descriptors**: Stable (PTY + FIFO, cleaned up properly)

### Reliability
- **Data Loss**: None (proven by test suite)
- **Deadlocks**: Eliminated (no circular dependencies)
- **Resource Leaks**: None (graceful cleanup paths)

## Testing Strategy

### Unit Tests Validate:
1. **Graceful exit** when subprocess already completed
2. **Forced exit** when subprocess still running  
3. **Exit code preservation** (0 vs -15 vs original subprocess code)
4. **Snapshot availability** after subprocess completion
5. **Command processing** during quiescence periods

### Integration Tests Validate:
1. **End-to-end flows** with real subprocesses
2. **Timing behavior** under various loads
3. **Error conditions** and recovery
4. **Resource cleanup** after abnormal termination

## Future Improvements

### Possible Optimizations:
1. **Adaptive quiescence periods** based on command frequency
2. **Faster FIFO detection** for very short-lived commands
3. **Configurable timeouts** for different use cases
4. **Metrics collection** for monitoring coordination health

### Architecture Extensions:
1. **Multiple subprocess support** with separate coordination
2. **Snapshot streaming** while subprocess still running
3. **Command replay** for deterministic testing
4. **Remote coordination** over network protocols

---

This coordination pattern ensures **reliable, fast, and data-safe** terminal automation while supporting both interactive and programmatic use cases. The key insight is **separating subprocess completion detection from output capture completion**, allowing independent optimization of both concerns. 