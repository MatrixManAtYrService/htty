# htty - Headless Terminal

A Python library for terminal automation using a headless terminal interface.

## Installation

```bash
pip install htty
```

This will automatically install `htty-core` as a dependency, which provides the underlying Rust binary.

## Quick Start

```python
import htty

# Run a command and capture output
with htty.terminal_session("echo 'Hello World'") as proc:
    snapshot = proc.snapshot()
    print(snapshot.text)
```

## Command Line Tools

After installation, you get the `htty` command for terminal automation tasks.

## Documentation

[Full documentation and examples coming soon]

## Architecture

This package depends on [`htty-core`](../htty-core/README.md), which contains the Rust binary with minimal Python bindings. This two-package approach works around maturin limitations while providing a clean user experience.

## See also

- **[htty-core](../htty-core/README.md)** - The underlying Rust binary package
- **[Project README](../README.md)** - Overview of the entire project