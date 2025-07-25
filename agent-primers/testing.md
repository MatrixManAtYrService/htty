# Testing Strategy: Environment-Aware Development

This document explains htty's testing strategy, which maps tests to specific devshell environments based on their dependencies. This approach enables fast iteration on different layers of the stack while providing integration testing.

## Architecture Overview

htty is built in layers:
1. htty-core - Maturin-built package (Rust binary + minimal Python bindings)
2. htty - Pure Python wrapper that depends on htty-core and adds higher-level functionality
3. htty-cli - Command-line tools without Python environment pollution

## Testing Environments & Pytest Marks

Pytest marks declare what environment each test needs, mapped to specialized Nix devshells:

### `@pytest.mark.empty` → `pytest-empty` devshell
- Purpose: Test nix functionality without any htty packages
- Contains: Only pytest and test dependencies
- Use Cases: External integration tests, nix package access verification

### `@pytest.mark.core` → `pytest-core` devshell
- Purpose: Test htty-core in isolation (Rust + minimal Python bindings)
- Contains: htty-core-env (maturin-built wheel)
- Use Cases: Test Python/Rust bridge, basic terminal operations, htty_core module functionality

### `@pytest.mark.wheel` → `pytest-wheel` devshell
- Purpose: Test htty-core-wheel package for Python wheel creation
- Contains: htty-core-wheel package for building .whl files
- Use Cases: Verify wheel packaging, metadata files, wheel file naming

### `@pytest.mark.cli` → `pytest-cli` devshell
- Purpose: Test CLI tools without Python environment pollution
- Contains: htty-cli package (htty command only, no Python modules in PATH)
- Use Cases: Command-line interface testing, verifying no Python environment leakage

### `@pytest.mark.htty` → `pytest-htty` devshell
- Purpose: Complete integration testing (htty-core + htty wrapper)
- Contains: Complete htty environment for integration tests
- Use Cases: End-to-end workflows, full integration tests, realistic user scenarios

### `@pytest.mark.sdist` → `pytest-sdist` devshell
- Purpose: Test htty-sdist package for source distribution creation
- Contains: htty-sdist package for building .tar.gz files
- Use Cases: Verify source distribution packaging, metadata files, build artifacts

## Running Tests

### Fast Development Iteration
```bash
# Core functionality tests (medium build time)
nix develop .#pytest-core --command pytest -vs -m core

# Wheel packaging tests (fast)
nix develop .#pytest-wheel --command pytest -vs -m wheel

# CLI tool tests (fast)
nix develop .#pytest-cli --command pytest -vs -m cli
```

### Integration Testing
```bash
# Complete environment tests
nix develop .#pytest-htty --command pytest -vs -m htty

# Wheel packaging tests
nix develop .#pytest-wheel --command pytest -vs -m wheel

# Source distribution tests
nix develop .#pytest-sdist --command pytest -vs -m sdist

# External integration tests
nix develop .#pytest-empty --command pytest -vs -m empty
```

### Run All Tests
```bash
# Run each test suite in appropriate environment
nix develop .#pytest-empty --command pytest -vs -m empty
nix develop .#pytest-core --command pytest -vs -m core
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-cli --command pytest -vs -m cli
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-htty --command pytest -vs -m htty
```

## Test Organization

Tests are organized by functionality in folders, and environmental dependencies via marks:

```
tests/
├── env_tests/         # Environment verification tests
├── py_unit_tests/     # Python-specific unit tests
├── lib_tests/         # Core library functionality tests
└── cli_tests/         # Command-line interface tests
```

Each test file can contain tests with different marks for different layers:

```python
# tests/lib_tests/test_terminal.py

@pytest.mark.core
def test_htty_core_process():
    """Core test: basic htty_core functionality"""
    import htty_core
    proc = htty_core.create_process(["echo", "hello"])
    # Test htty_core directly

@pytest.mark.htty
def test_complete_workflow():
    """Integration test: full htty workflow"""
    import htty
    with htty.terminal_session("cat", rows=10, cols=20) as session:
        session.send_keys("hello")
        assert "hello" in session.snapshot().text
```

## Key Benefits

### 1. Fast Iteration
- Python changes don't trigger Rust rebuilds when using htty package
- Rust changes only affect environments that need them
- Each layer can be developed independently

### 2. Clear Separation
- Tests declare exactly what they need via marks
- Matches the actual package architecture
- Easy to debug issues at specific layers

### 3. Comprehensive Coverage
- Integration tests with real components (core, full)
- CLI tests without Python environment pollution (cli)
- External verification tests (empty)

## When to Use Each Mark

### Use `@pytest.mark.core` when:
- Testing htty_core functionality directly
- Testing the Python/Rust bridge
- Validating basic terminal operations
- Testing binary integration points

### Use `@pytest.mark.wheel` when:
- Testing Python wheel packaging
- Verifying .whl file creation and naming
- Testing wheel metadata files
- Validating maturin build outputs

### Use `@pytest.mark.cli` when:
- Testing command-line interface behavior
- Verifying CLI tools work without Python environment issues
- Testing script integration

### Use `@pytest.mark.htty` when:
- Testing complete end-to-end workflows
- Need realistic user environment
- Testing integration between htty and htty_core
- Validating final user experience

### Use `@pytest.mark.sdist` when:
- Testing source distribution packaging
- Verifying .tar.gz file creation
- Testing metadata file generation
- Validating build artifacts

### Use `@pytest.mark.empty` when:
- Testing nix package functionality
- Verifying external integration
- Testing that environments properly isolate dependencies

## Development Workflow

### Working on Rust Integration (htty-core)
```bash
# Test Rust+Python bridge
nix develop .#pytest-core --command pytest -vs -m core

# Test wheel packaging
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

### Working on Complete Features
```bash
# Complete environment for integration work
nix develop .#pytest-htty --command pytest -vs -m htty
```

### Before Committing
```bash
# Run all test suites to ensure nothing breaks
nix develop .#pytest-empty --command pytest -vs -m empty
nix develop .#pytest-core --command pytest -vs -m core
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-cli --command pytest -vs -m cli
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-htty --command pytest -vs -m htty
```

## Fresh Code Guarantee

All environments automatically rebuild when source code changes:
- htty-core changes → Rebuilds: htty-core-wheel → htty-core-env, htty → pytest-core, pytest-wheel, pytest-htty
- htty changes → Rebuilds: htty → pytest-htty, pytest-sdist
- Test changes → All pytest environments rebuild test dependencies

This ensures you always test fresh code and never encounter stale environment issues.

## Important Notes

### Environment Isolation
Each environment provides only what's declared:
- pytest-cli: CLI tools but no Python modules in PYTHONPATH
- pytest-empty: No htty packages at all
- pytest-core: Only htty_core, no high-level htty wrapper
- pytest-wheel: htty-core-wheel package for Python wheel testing
- pytest-sdist: htty-sdist package for source distribution testing
- pytest-htty: Complete environment with htty package

This isolation ensures tests can't accidentally depend on components they shouldn't have access to.