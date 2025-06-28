# htty - Headless Terminal Automation

![CI](https://github.com/MatrixManAtYrService/htty/workflows/CI/badge.svg)

**htty** programmatically captures the appearance of terminal applications and automates interactions with them. It's perfect for testing CLI tools, automating terminal workflows, and capturing terminal output as it appears to users.

## What is htty?

htty solves a common problem: terminal applications don't behave the same way when you try to capture their output programmatically. Consider vim's startup screen:

```
~                       VIM - Vi IMproved
~                       version 9.1.1336
~                   by Bram Moolenaar et al.
~          Vim is open source and freely distributable
~
~                 Help poor children in Uganda!
```

If you try to capture this with standard subprocess tools, you won't get the nicely formatted text you see above. Instead, you'll get raw ANSI escape sequences.

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;32HHelp poor children in Uganda!
```

htty connects your subprocess to a **headless terminal** (pseudoterminal) and handles all the ANSI escape sequences, giving you the exact text and formatting that a user would see.



### Python API

```python
import htty
from htty import Press

# Context manager approach (recommended)
with htty.terminal_session("vim", rows=20, cols=50) as proc:
    proc.send_keys("i")           # Enter insert mode
    proc.send_keys("Hello world!") # Type text
    proc.send_keys(Press.ESCAPE)   # Exit insert mode

    snapshot = proc.snapshot()
    print(snapshot.text)          # Plain text
    print(snapshot.html)          # HTML with colors

    proc.send_keys(":q!")         # Quit without saving
    proc.send_keys(Press.ENTER)

# Direct control approach
proc = htty.run("echo hello", rows=10, cols=40)
snapshot = proc.snapshot()
print(snapshot.text)  # "hello"
exit_code = proc.exit()
```

### Command Line Interface

```bash
# Simple command execution
htty -- echo "hello world"

# Interactive commands with key sending
htty -k "world,Enter" -- python3 -c "print('hello', input())"

# Multiple snapshots during execution
htty --snapshot -k "ihello,Escape" --snapshot -k ":q!,Enter" -- vim

# Custom terminal size
htty -r 24 -c 80 -- htop
```

## Use Cases

### Testing CLI Applications

```python
def test_my_cli_tool():
    with htty.terminal_session("my-cli-tool --interactive", rows=10, cols=50) as proc:
        # Send user input
        proc.send_keys("option1")
        proc.send_keys(Press.ENTER)

        # Verify output
        snapshot = proc.snapshot()
        assert "Success!" in snapshot.text
```

### Automating Terminal Workflows

```python
# Automate a vim editing session
with htty.terminal_session("vim myfile.txt", rows=24, cols=80) as proc:
    proc.send_keys("i")                    # Insert mode
    proc.send_keys("Hello, World!")        # Type content
    proc.send_keys(Press.ESCAPE)           # Normal mode
    proc.send_keys(":wq")                  # Save and quit
    proc.send_keys(Press.ENTER)
```

### Capturing Colored Output

```python
# Capture output with ANSI colors preserved
proc = htty.run("ls --color=always", rows=10, cols=50)
snapshot = proc.snapshot()

# Get plain text
print(snapshot.text)

# Get HTML with colors
with open("output.html", "w") as f:
    f.write(snapshot.html)
```

## Key Concepts

### Snapshots
A snapshot captures the current state of the terminal screen:
- `snapshot.text` - Plain text content
- `snapshot.html` - HTML with ANSI colors converted to CSS

### Key Sending
Send individual characters or special keys:
```python
proc.send_keys("hello")           # Individual characters
proc.send_keys(Press.ENTER)       # Special keys
proc.send_keys(Press.ESCAPE)      # More special keys
proc.send_keys("text,Enter,Escape") # CLI-style comma-separated
```

### Process Management
htty handles subprocess lifecycle automatically:
- Context managers clean up automatically
- `proc.exit()` for manual cleanup
- Proper signal handling for forced termination

## CLI Reference

```bash
htty [OPTIONS] -- COMMAND [ARGS...]

Options:
  -r, --rows ROWS        Terminal height (default: 24)
  -c, --cols COLS        Terminal width (default: 80)
  -k, --keys KEYS        Send keys (comma-separated)
  --snapshot             Take a snapshot
  --help                 Show help message

Examples:
  htty -- echo hello                    # Simple execution
  htty -k "Enter" -- python3            # Send Enter key
  htty --snapshot -- vim                # Take snapshot
  htty -r 30 -c 100 -- htop            # Custom size
```

## Advanced Usage

### Multiple Snapshots

```python
proc = htty.run("vim", rows=20, cols=50)

# Initial snapshot
snap1 = proc.snapshot()

# Make changes
proc.send_keys("i")
proc.send_keys("Hello")
proc.send_keys(Press.ESCAPE)

# Another snapshot
snap2 = proc.snapshot()

proc.send_keys(":q!")
proc.send_keys(Press.ENTER)
proc.exit()
```

### Error Handling

```python
try:
    with htty.terminal_session("nonexistent-command") as proc:
        snapshot = proc.snapshot()
except Exception as e:
    print(f"Command failed: {e}")
```

### Custom Logging

```python
import logging

logger = logging.getLogger("my_test")
proc = htty.run("vim", rows=20, cols=50, logger=logger)
```

## How It Works

htty is built on top of a Rust binary that:
1. Creates a pseudoterminal (PTY)
2. Launches your subprocess connected to the PTY
3. Captures all terminal output and input
4. Processes ANSI escape sequences
5. Maintains the terminal state (cursor position, colors, etc.)
6. Provides snapshots of the current screen

The Python library communicates with this Rust binary via JSON over stdin/stdout, providing a clean API for terminal automation.

## Comparison to Other Tools

| Tool | Use Case | Pros | Cons |
|------|----------|------|------|
| `subprocess` | Simple command execution | Built-in, fast | No terminal emulation |
| `pexpect` | Interactive automation | Mature, widely used | Complex API, Unix-only |
| `htty` | Terminal automation & testing | True terminal rendering, cross-platform | Newer project |

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and testing guidelines.

## License

Apache License, Version 2.0. This project is a fork of [ht](https://github.com/andyk/ht) with Python bindings and enhanced automation features.
