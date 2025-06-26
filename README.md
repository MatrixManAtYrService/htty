# htty - Headless Terminal with Python Bindings

A Python library and CLI tool for terminal automation, built on a Rust binary for high performance and reliability.

## 🚀 Quick Start

### For Users

```bash
# CLI tools (ht + htty commands)
nix run github:MatrixManAtYrService/ht#htty-cli

# Python library environment  
nix shell github:MatrixManAtYrService/ht#htty-pylib
python -c "import htty; print('Ready!')"
```

### For Development

```bash
git clone https://github.com/MatrixManAtYrService/ht
cd ht

# Enter development environment
nix develop

# Run tests with fresh code every time
nix develop .#pytest --command pytest tests/lib_tests/ -v
```

## 📝 Python API

```python
import htty

# Context manager approach (recommended)
with htty.ht_process("vim", rows=20, cols=50) as proc:
    proc.send_keys(["i", "Hello world!", htty.Press.ESCAPE])
    snapshot = proc.snapshot()
    print(snapshot.text)
    proc.send_keys([":q!", htty.Press.ENTER])

# Direct control
proc = htty.run(["echo", "hello"], rows=10, cols=40)
snapshot = proc.snapshot()
proc.exit()
```

## 🔧 Development Workflow

### The Fresh Code Guarantee

This project uses **Nix with uv2nix** to ensure that every test run uses fresh, up-to-date code with no stale virtual environment issues.

**❌ Don't do this:**
```bash
# These create imperative state that can become stale
pip install -e .
uv run pytest tests/
python -m venv .venv && source .venv/bin/activate
```

**✅ Do this instead:**
```bash
# Fresh environment every time, testing exactly what users get
nix develop .#pytest --command pytest tests/lib_tests/test_htty.py -v -s
```

### Why This Works

1. **No Stale Code**: Every test run rebuilds the environment from scratch
2. **Testing Reality**: You test the exact same `htty-pylib` package that users receive  
3. **Immediate Feedback**: Code changes in Rust (`src/`) or Python (`python/`) are reflected instantly
4. **Dependency Isolation**: Test dependencies (pytest) are separate from the library being tested

### The Two-Environment Architecture

- **`htty-pylib`**: The exact Python environment users get when they install htty
- **`test-deps-only`**: Pytest and testing tools, added on top via uv2nix
- **Combined**: PYTHONPATH makes both available, with htty taking priority

This separation ensures you're always testing the real thing, not a development approximation.

### Development Commands

```bash
# Test specific module
nix develop .#pytest --command pytest tests/lib_tests/test_htty.py::test_hello_world -v -s

# Test all lib tests  
nix develop .#pytest --command pytest tests/lib_tests/ -v

# Check that code changes are reflected
nix develop .#pytest --command pytest tests/lib_tests/test_help_freshness.py -v

# Interactive development
nix develop .#pytest
# Now you have: pytest, python with htty, and fresh code guaranteed
```

### Making Changes

1. **Edit code** in `src/` (Rust) or `python/` (Python)
2. **Add to git**: `git add .` (Nix flakes need to see changes)
3. **Test immediately**: The test command will rebuild automatically

The build system handles:
- Rebuilding the Rust binary when `src/` changes
- Rebuilding the Python wheel when `python/` changes  
- Creating fresh environments with updated code
- No manual build steps required

## 📦 Package Structure

- **`htty-cli`** - CLI tools (ht + htty) with zero Python pollution
- **`htty-pylib`** - Clean Python environment with htty library
- **`htty-wheel`** - Python wheel for integration with other tools

## 🎯 Core Features

- **Reliable subprocess management** - No race conditions in terminal automation
- **JSON API** - Simple interface for programmatic control
- **Context managers** - Automatic cleanup of processes and resources
- **Live preview** - HTTP server for real-time terminal visualization

## 🤝 Contributing

1. Fork the repository
2. Make changes in `src/` (Rust) or `python/` (Python)  
3. Add files to git: `git add .`
4. Test: `nix develop .#pytest --command pytest tests/lib_tests/ -v`
5. Submit a pull request

The Nix-based workflow ensures that your changes work in a clean environment and that tests are reliable.

## 📄 License

Apache License, Version 2.0. Fork of [ht](https://github.com/andyk/ht) with Python bindings.
