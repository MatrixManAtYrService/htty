# htty-core

This is a minimal distribution package containing the Rust `ht` binary with basic Python bindings. It exists solely as a dependency for the main [`htty`](../htty/README.md) package.

**You probably want [`htty`](../htty/README.md) instead** - it provides the full Python library and command-line tools.

## Why this exists

This package works around a maturin limitation: you can't include both console scripts and PyO3 bindings in the same project. So we split into two packages:

- **htty-core** (this package): Contains the Rust binary with minimal Python bindings
- **htty**: Depends on htty-core and provides the full Python API and CLI tools

## See also

- **[htty](../htty/README.md)** - The main package you want to use
- **[Project README](../README.md)** - Overview of the entire project