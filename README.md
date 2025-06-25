# htty - Headless Terminal with Python Bindings

`htty` is a Python library and CLI tool for terminal automation, built on top of a fork of the [`ht`](https://github.com/andyk/ht) headless terminal. It provides both a high-performance Rust binary and comprehensive Python bindings for programmatic terminal interaction.

<img src="https://andykonwinski.com/assets/img/headless-terminal.png" alt="screenshot of raw terminal output vs ht output" align="right" style="width:450px">

## 🎯 Features

- **Two CLI Modes**: 
  - `ht` - Async passthrough to the underlying ht binary (original behavior)
  - `htty` - Synchronous batch processing mode for scripting
- **Python Library**: Full-featured Python API with context managers and subprocess control
- **Reliable Subprocess Management**: Built on enhanced ht with `--start-on-output` and `exit` commands
- **No Race Conditions**: Eliminates timing issues common in terminal automation
- **JSON API**: Simple, well-defined interface for terminal interaction
- **Live Preview**: Built-in HTTP server for real-time terminal visualization

## 🚀 Quick Start

### Installation

Install from source using Nix (recommended):

```bash
# Both CLI tools without Python environment pollution
nix build github:MatrixManAtYrService/ht#htty-cli

# Python library environment
nix build github:MatrixManAtYrService/ht#htty-pylib

# Or for development - individual components:
nix build github:MatrixManAtYrService/ht#htty        # Rust binary with Python features
nix build github:MatrixManAtYrService/ht#htty-wheel  # Python wheel
nix build github:MatrixManAtYrService/ht#htty-test   # Test environment
```

Or build from source:

```bash
git clone https://github.com/MatrixManAtYrService/ht
cd ht
nix develop  # Sets up development environment
maturin develop --features python
```

### Using as a Flake Input

Add to your `flake.nix`:

```nix
{
  inputs = {
    htty.url = "github:MatrixManAtYrService/ht";
  };

  outputs = { self, nixpkgs, htty }: {
    devShells.default = pkgs.mkShell {
      packages = [ 
        # For CLI usage - both ht and htty commands, zero Python pollution
        htty.packages.${system}.htty-cli
        
        # For Python development - clean Python environment with htty library
        # htty.packages.${system}.htty-pylib
      ];
    };
  };
}
```

### 🎛️ **Command Examples**

```bash
# htty-cli provides both:
ht --listen 8080 -- vim              # Rust binary (async mode)
htty -s -- echo "Hello World"        # Python CLI (sync mode)

# htty-pylib provides:
python -c "import htty; print('📚')" # Library usage
python -m htty -s -- echo "Hello"    # CLI via Python module
```

### CLI Usage

```bash
# Synchronous batch mode - perfect for scripting
htty -k "hello,Enter" -s -- vim
htty -r 30 -c 80 -s -k "ihello,Escape" -s -k ":q!,Enter" -- vim

# Async mode - original ht behavior  
ht --subscribe snapshot -- vim
ht --listen 127.0.0.1:8080 -- bash
```

### Python Library Usage

```python
import htty

# Context manager approach (recommended)
with htty.ht_process("vim", rows=20, cols=50) as proc:
    proc.send_keys([htty.Press.ENTER])
    snapshot = proc.snapshot()
    print(snapshot.text)

# Direct subprocess control
proc = htty.run(["echo", "hello"], rows=10, cols=40)
proc.send_keys(["world", htty.Press.ENTER])
snapshot = proc.snapshot()
proc.exit()
```

## 📚 Documentation

### Python API

#### Key Classes

- **`htty.Press`** - Key constants (`ENTER`, `TAB`, `CTRL_C`, `ESCAPE`, etc.)
- **`htty.HTProcess`** - Main subprocess controller
- **`htty.SnapshotResult`** - Snapshot data with `.text`, `.html`, and `.raw_seq`
- **`htty.ht_process()`** - Context manager for automatic cleanup

#### Example: Automating vim

```python
import htty

with htty.ht_process("vim", rows=24, cols=80) as proc:
    # Enter insert mode and type
    proc.send_keys(["i", "Hello, World!"])
    
    # Exit insert mode and save
    proc.send_keys([htty.Press.ESCAPE, ":w test.txt", htty.Press.ENTER])
    
    # Take a snapshot
    snapshot = proc.snapshot()
    print("Current screen:")
    print(snapshot.text)
    
    # Quit vim
    proc.send_keys([":q", htty.Press.ENTER])
```

### CLI Reference

#### htty (Synchronous Mode)

```bash
htty [OPTIONS] -- COMMAND [ARGS...]

Options:
  -r, --rows <N>          Terminal rows (default: 20)
  -c, --cols <N>          Terminal columns (default: 50) 
  -k, --keys <KEYS>       Send comma-separated keys
  -s, --snapshot          Take terminal snapshot
  -d, --delimiter <CHAR>  Key delimiter (default: ",")

# Actions are processed in order:
htty -k "vim" -k "Enter" -s -k "ihello" -s -k "Escape" -s -- bash
```

#### Key Specifications

Special keys: `Enter`, `Tab`, `Escape`, `Space`, `Up`, `Down`, `Left`, `Right`, `Backspace`

Control sequences: `C-c`, `C-d`, etc.

### Underlying ht API

htty builds on the enhanced `ht` binary which provides:

#### STDIO Commands

Send JSON commands to stdin:

```json
{"type": "sendKeys", "keys": ["hello", "Enter"]}
{"type": "takeSnapshot"}
{"type": "exit"}
{"type": "resize", "cols": 80, "rows": 24}
```

#### Event Subscription

```bash
ht --subscribe snapshot,output,pid -- command
```

Events are output as JSON:
- `snapshot` - Terminal state capture
- `output` - Raw terminal output  
- `pid` - Subprocess process ID
- `exitCode` - Process exit status
- `resize` - Terminal size changes

## 🔧 Development

## 📦 Nix Flake Outputs

This project provides several Nix packages optimized for different use cases:

### 🎯 **For End Users**

- **`htty-cli`** - **Both CLI tools (`ht` + `htty`)** 
  - Contains the native Rust `ht` binary (async terminal automation)
  - Contains the Python `htty` CLI (synchronous batch scripting)
  - **Zero Python environment pollution** - perfect for devshells
  - Use when you want both CLI tools without any Python dependency bloat

- **`htty-pylib`** - **Python library environment**
  - Clean Python environment with `htty` library installed
  - For Python development and scripting with htty
  - Includes `python -m htty` CLI access
  - Use when you need to import htty in Python code

### ⚙️ **For Development & Integration**

- **`htty`** - Full Rust binary with Python features (for project development)
- **`htty-wheel`** - Python wheel file (for integration with uv2nix and other packaging)
- **`htty-test`** - Test environment with htty wheel installed (for CI/testing)

### 🔍 **Key Differences: CLI vs PyLib**

| Package | Contains | Python Deps | Use Case |
|---------|----------|-------------|----------|
| `htty-cli` | `ht` + `htty` binaries | ❌ None | DevShells, CLI users |
| `htty-pylib` | Python environment | ✅ Full Python | Python development |

**Why separate packages?** Prevents the infamous Nixpkgs Python setup hook issues that cause environment pollution and version conflicts in mixed-language projects.

### Building

```bash
# Development environment
nix develop

# Build individual packages
nix build .#htty-cli      # CLI only
nix build .#htty-pylib    # Python library
nix build .#htty-wheel    # Python wheel
nix build .#htty-test     # Test environment

# Traditional builds
cargo build --release               # Rust binary only
maturin develop --features python   # Python wheel
```

### Testing

```bash
# Run basic functionality tests
nix build .#htty-test
./result/bin/htty-test

# Run pytest in the test environment  
./result/bin/htty-pytest test_basic.py

# Traditional testing
cargo test                # Rust tests
python -m pytest         # Python tests (when available)
```

### Architecture

htty consists of:

1. **Enhanced ht binary** (Rust) - Core terminal emulation with reliability improvements
2. **Python bindings** (PyO3) - Subprocess controller wrapping the ht binary  
3. **CLI tools** - Both async and sync interfaces
4. **Nix packaging** - Clean separation between CLI and Python library consumers

The Nix package structure follows best practices:
- **CLI-only package** prevents Python environment pollution in devshells
- **Python library package** provides clean Python environment for development
- **Wheel package** enables integration with uv2nix and other Python packaging tools
- **Test environment** uses the wheel as input, demonstrating proper separation of concerns

Key improvements over original ht:
- **`--start-on-output`** - Eliminates race conditions by waiting for subprocess output
- **`exit` command** - Provides clean process termination
- **Enhanced error handling** - Better subprocess lifecycle management

## 🎯 Use Cases

- **Terminal Testing** - Automated testing of CLI applications
- **AI Agent Integration** - LLMs interacting with terminals like humans
- **DevOps Automation** - Scripted terminal workflows  
- **Documentation** - Generating terminal session recordings
- **Interactive Tutorials** - Programmatic terminal demonstrations

## 🔄 Migration from ht

htty is a fork of ht with additional Python integration. The core ht functionality remains unchanged:

```bash
# Original ht usage still works
ht --size 80x24 --subscribe snapshot -- vim

# Now also available as
htty -c 80 -r 24 -s -- vim  # Synchronous snapshot
```

## 📖 Related Projects

- [ht (original)](https://github.com/andyk/ht) - The upstream headless terminal project
- [expect](https://core.tcl-lang.org/expect/index) - Classic terminal automation tool
- [pexpect](https://pexpect.readthedocs.io/) - Python expect-like library

## 🔧 Development Status (June 2025)

### ✅ What's Working

- **Core Rust Binary**: The `ht` binary builds successfully and provides headless terminal functionality
- **Basic Python Bindings**: Python module can be imported and core classes are functional
  - `htty.Press` constants (ENTER, TAB, ESCAPE, etc.) work correctly
  - `htty.run()` function can start processes
  - `htty.ht_process()` context manager works
  - Basic `send_keys()` and `snapshot()` methods are implemented

### ⚠️ Current Issues & Limitations

- **Snapshot Timeout**: The `snapshot()` method times out for quick commands like `echo`
- **Missing Methods**: Some test-expected methods are not yet implemented:
  - `subprocess_controller.wait()`
  - `get_output()` for retrieving output events
  - `terminate()` and related cleanup methods
- **Python Version Compatibility**: Requires `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` for Python 3.13

### 🛠 Development Setup (Working)

```bash
# Clone and enter directory
cd /Users/matt/src/ht

# Build Rust binary
nix build .#htty --print-out-paths

# Build Python wheel in development environment
nix develop --command bash -c '
  python -m venv .venv 
  source .venv/bin/activate
  PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --features python
'

# Test basic functionality
export PATH="/nix/store/...-htty-0.3.0/bin:$PATH"  # Use actual build path
source .venv/bin/activate
python test_basic.py  # Basic import/class tests pass
```

### 🚧 Next Steps

1. **Fix Snapshot Issues**: Debug why snapshots timeout on simple commands
2. **Complete Python API**: Implement missing methods expected by test suite
3. **Blueprint Integration**: Update flake.nix to use blueprint like htty project
4. **Test Suite**: Get `/Users/matt/src/htty/tests/test_ht_util.py` fully passing
5. **Error Handling**: Improve error messages and timeouts

### 📝 Testing Notes

- Basic Python import works: `import htty` ✅
- Process creation works: `htty.run(["echo", "test"])` ✅ 
- Context manager works: `with htty.ht_process([...])` ✅
- Key constants work: `htty.Press.ENTER` ✅
- Snapshot method exists but times out on quick commands ⚠️

The foundation is solid - the Rust-Python integration works and the basic API is functional. Main work needed is completing the Python API surface and debugging the snapshot timing issues.

## 🤝 Contributing

Contributions welcome! This project maintains compatibility with the upstream ht project while adding Python-specific enhancements.

## 📄 License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

This project is a fork of [ht](https://github.com/andyk/ht) with additional Python bindings and enhanced reliability features.
