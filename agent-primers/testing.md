# Testing Strategy: Environment-Aware Development

This document explains htty's testing strategy, which maps tests to specific devshell environments based on their dependencies. This approach enables fast iteration on different layers of the stack while providing comprehensive integration testing.

## Architecture Overview

htty is built in layers:
1. **htty-core** - Maturin-built package (Rust binary + minimal Python bindings)
2. **htty** - Pure Python wrapper that depends on htty-core and adds higher-level functionality
3. **htty-cli** - Command-line tools without Python environment pollution

## Testing Environments & Pytest Marks

We use pytest marks to explicitly declare what environment each test needs, then map those marks to specialized Nix devshells:

### `@pytest.mark.empty` → `pytest-empty` devshell
- **Purpose**: Test nix functionality without any htty packages
- **Contains**: Only pytest and test dependencies
- **Use Cases**: External integration tests, nix package access verification

### `@pytest.mark.core` → `pytest-core` devshell
- **Purpose**: Test htty-core in isolation (Rust + minimal Python bindings)
- **Contains**: htty-core-env (maturin-built wheel)
- **Use Cases**: Test Python/Rust bridge, basic terminal operations, htty_core module functionality

### `@pytest.mark.sdist` → `pytest-sdist` devshell
- **Purpose**: Test pure Python htty package without htty-core
- **Contains**: htty Python package with htty_core dependency removed
- **Use Cases**: Pure Python logic, mocked testing, argument parsing
- **Note**: htty_core imports will fail - tests must mock this dependency

### `@pytest.mark.cli` → `pytest-cli` devshell
- **Purpose**: Test CLI tools without Python environment pollution
- **Contains**: htty-cli package (htty command only, no Python modules in PATH)
- **Use Cases**: Command-line interface testing, verifying no Python environment leakage

### `@pytest.mark.full` → `pytest-full` devshell
- **Purpose**: Complete integration testing (htty-core + htty wrapper)
- **Contains**: Complete htty environment + testVim for integration tests
- **Use Cases**: End-to-end workflows, full integration tests, realistic user scenarios

## Running Tests

### Fast Development Iteration
```bash
# Python-only unit tests (3s build, htty_core must be mocked)
nix develop .#pytest-sdist --command pytest -vs -m sdist

# Core functionality tests (medium build time)
nix develop .#pytest-core --command pytest -vs -m core

# CLI tool tests (fast)
nix develop .#pytest-cli --command pytest -vs -m cli
```

### Integration Testing
```bash
# Full environment tests (22s build time)
nix develop .#pytest-full --command pytest -vs -m full

# External integration tests
nix develop .#pytest-empty --command pytest -vs -m empty
```

### Run All Tests
```bash
# Run each test suite in appropriate environment
nix develop .#pytest-empty --command pytest -vs -m empty
nix develop .#pytest-core --command pytest -vs -m core
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-cli --command pytest -vs -m cli
nix develop .#pytest-full --command pytest -vs -m full
```

## Test Organization

Tests are organized by **functionality** in folders, and **environmental dependencies** via marks:

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

@pytest.mark.sdist
def test_parse_terminal_size():
    """Unit test: parse size string (Python-only, mock htty_core)"""
    # This test must mock htty_core since it's not available
    assert parse_size("80x24") == (80, 24)

@pytest.mark.core
def test_htty_core_process():
    """Core test: basic htty_core functionality"""
    import htty_core
    proc = htty_core.create_process(["echo", "hello"])
    # Test htty_core directly

@pytest.mark.full
def test_complete_workflow():
    """Integration test: full htty workflow"""
    import htty
    with htty.terminal_session("cat", rows=10, cols=20) as session:
        session.send_keys("hello")
        assert "hello" in session.snapshot().text
```

## Key Benefits

### 1. **Fast Iteration**
- Python changes don't trigger Rust rebuilds in sdist environment
- Rust changes only affect environments that need them
- Each layer can be developed independently

### 2. **Clear Separation**
- Tests declare exactly what they need via marks
- Matches the actual package architecture
- Easy to debug issues at specific layers

### 3. **Comprehensive Coverage**
- Unit tests with mocked dependencies (sdist)
- Integration tests with real components (core, full)
- CLI tests without Python pollution (cli)
- External verification tests (empty)

## When to Use Each Mark

### Use `@pytest.mark.sdist` when:
- Testing pure Python logic that doesn't need htty_core
- Working with mocked dependencies
- Need fastest possible iteration cycles
- Testing argument parsing, data structures, algorithms

### Use `@pytest.mark.core` when:
- Testing htty_core functionality directly
- Testing the Python/Rust bridge
- Validating basic terminal operations
- Testing binary integration points

### Use `@pytest.mark.cli` when:
- Testing command-line interface behavior
- Verifying CLI tools work without Python environment issues
- Testing script integration

### Use `@pytest.mark.full` when:
- Testing complete end-to-end workflows
- Need realistic user environment
- Testing integration between htty and htty_core
- Validating final user experience

### Use `@pytest.mark.empty` when:
- Testing nix package functionality
- Verifying external integration
- Testing that environments properly isolate dependencies

## Development Workflow

### Working on Python Logic (htty wrapper)
```bash
# Fast feedback loop - mock htty_core in tests
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

### Working on Rust Integration (htty-core)
```bash
# Test Rust+Python bridge
nix develop .#pytest-core --command pytest -vs -m core
```

### Working on Complete Features
```bash
# Full environment for integration work
nix develop .#pytest-full --command pytest -vs -m full
```

### Before Committing
```bash
# Run all test suites to ensure nothing breaks
nix develop .#pytest-empty --command pytest -vs -m empty
nix develop .#pytest-core --command pytest -vs -m core
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-cli --command pytest -vs -m cli
nix develop .#pytest-full --command pytest -vs -m full
```

## Fresh Code Guarantee

All environments automatically rebuild when source code changes:
- **htty-core changes** → Rebuilds: htty-core-wheel → htty-core-env, htty → pytest-core, pytest-full
- **htty changes** → Rebuilds: htty → pytest-full, pytest-sdist (Python parts)
- **Test changes** → All pytest environments rebuild test dependencies

This ensures you always test fresh code and never encounter stale environment issues.

## Important Notes

### Mocking in sdist Environment
The sdist environment removes htty_core dependency, so imports like `import htty_core` will fail. Tests must mock this:

```python
@pytest.mark.sdist
def test_with_mocked_core():
    from unittest.mock import patch
    with patch('htty.core.htty_core'):
        # Test htty logic with mocked htty_core
        pass
```

### Environment Isolation
Each environment provides only what's declared:
- **pytest-cli**: CLI tools but no Python modules in PYTHONPATH
- **pytest-empty**: No htty packages at all
- **pytest-sdist**: Python htty but no htty_core
- **pytest-core**: Only htty_core, no high-level htty wrapper
- **pytest-full**: Complete environment

This isolation ensures tests can't accidentally depend on components they shouldn't have access to.