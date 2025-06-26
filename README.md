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

## 🎯 Core Features

- **Reliable subprocess management** - No race conditions in terminal automation
- **JSON API** - Simple interface for programmatic control
- **Context managers** - Automatic cleanup of processes and resources
- **Live preview** - HTTP server for real-time terminal visualization

## 📖 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow and testing
- **[PACKAGING.md](PACKAGING.md)** - Build system architecture and package details

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow that ensures reliable testing with fresh code.

## 📄 License

Apache License, Version 2.0. Fork of [ht](https://github.com/andyk/ht) with Python bindings.
