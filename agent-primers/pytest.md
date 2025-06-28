# Pytest Marks Strategy: Environment-Aware Testing

This document explains htty's pytest marks strategy, which maps tests to specific devshell environments based on their dependencies. This approach enables fast iteration on unit tests while providing access to realistic integration environments when needed.

## Core Problem

Traditional test setups face a dilemma:
- **Fast unit tests** need minimal dependencies (Python-only) for quick iteration
- **Integration tests** need the full environment (Rust binary, system dependencies) to test realistic scenarios
- Building everything for every test wastes time and resources
- Running tests in the wrong environment leads to false positives/negatives

## Our Solution: Pytest Marks + Environment Mapping

We use pytest marks to explicitly declare what environment each test needs, then map those marks to specialized Nix devshells:

```python
@pytest.mark.sdist
def test_python_logic():
    """Pure Python test - no binary needed"""
    pass

@pytest.mark.wheel
def test_terminal_interaction():
    """Integration test - needs ht binary"""
    pass
```

## Available Marks & Environments

### `@pytest.mark.sdist` → `pytest-sdist` devshell
- **Purpose**: Pure Python unit testing with mocked binaries
- **htty Package**: Hatchling-built source distribution (Python-only)
- **Binary Access**: ❌ `ht` binary is NOT available (intentional)
- **Build Time**: ~3 seconds (Python-only, no Rust compilation)
- **Use Cases**:
  - Argument parsing logic
  - Data structure manipulation
  - Error handling paths
  - Mock-based testing

### `@pytest.mark.wheel` → `pytest-wheel` devshell
- **Purpose**: Full integration testing with real binary
- **htty Package**: Complete wheel with Rust binary included
- **Binary Access**: ✅ `ht` binary available
- **Build Time**: ~22 seconds (includes Rust compilation)
- **Use Cases**:
  - Terminal interaction flows
  - Subprocess coordination
  - End-to-end workflows
  - Real terminal output validation

## Usage Examples

### Running Fast Unit Tests Only
```bash
# Quick iteration on Python logic - 3s build time
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

### Running Integration Tests Only
```bash
# Full environment testing - 22s build time
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

### Running All Tests
```bash
# Run in appropriate environments (builds both as needed)
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

## Key Benefits

### 1. **Fast Iteration on Unit Tests**
- Pure Python tests run in 3s vs 22s
- No waiting for Rust compilation when testing Python logic
- Immediate feedback loop for TDD workflows

### 2. **Realistic Integration Testing**
- Integration tests run with the actual `ht` binary
- Same environment structure that users experience
- Catches real-world integration issues

### 3. **Explicit Dependency Declaration**
- Tests declare exactly what they need via marks
- No guessing about environmental requirements
- Clear separation between unit and integration tests

### 4. **Build Optimization**
- Nix only builds what's needed for the requested mark
- Source filtering prevents unnecessary rebuilds
- Cached builds when dependencies haven't changed

### 5. **Isolation Benefits**
- Pure Python tests can't accidentally depend on the binary
- Forces proper mocking and dependency injection
- Integration tests verify real binary behavior

## Test Organization Strategy

We use a two-dimensional organization:

**Folders** organize by **functionality**:
- `tests/lib_tests/` - Core library functionality
- `tests/py_unit_tests/` - Python-specific unit tests
- `tests/cli_tests/` - Command-line interface tests

**Marks** organize by **environmental dependencies**:
- `@pytest.mark.sdist` - Python-only dependencies
- `@pytest.mark.wheel` - Full binary dependencies

This means you can have both unit and integration tests for the same functionality:

```python
# tests/lib_tests/test_terminal.py

@pytest.mark.sdist
def test_parse_terminal_size():
    """Unit test: parse size string without binary"""
    assert parse_size("80x24") == (80, 24)

@pytest.mark.wheel
def test_actual_terminal_resize():
    """Integration test: real terminal resizing"""
    with terminal_session("cat", rows=10, cols=20) as session:
        session.resize(30, 40)
        assert session.snapshot().rows == 30
```

## Development Workflow

### Working on Python Logic
```bash
# Fast feedback loop for Python development
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

### Working on Terminal Integration
```bash
# Full environment for integration work
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

### Before Committing
```bash
# Run both test suites to ensure nothing breaks
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

## Implementation Details

### Pytest Configuration
Both `pyproject.toml` files define the custom marks:

```toml
[tool.pytest.ini_options]
markers = [
    "wheel: tests that require the htty wheel with ht binary",
    "sdist: tests that run with pure Python source distribution (no ht binary)"
]
```

### Devshell Environments
- **`pytest-sdist`**: Uses `htty-py-sdist` (hatchling-built Python-only package)
- **`pytest-wheel`**: Uses `htty-pylib` (maturin-built wheel with Rust binary)

### Source Filtering
Each environment includes only the files it needs:
- `pytest-sdist`: Only Python source files → faster builds
- `pytest-wheel`: Both Rust and Python files → complete functionality

## When to Use Each Mark

### Use `@pytest.mark.sdist` when:
- Testing pure Python logic
- Validating argument parsing
- Testing data structures and algorithms
- Working with mocked dependencies
- Need fast iteration cycles

### Use `@pytest.mark.wheel` when:
- Testing actual terminal interactions
- Validating subprocess behavior
- Testing binary integration points
- Need realistic user environment
- Testing end-to-end workflows

## Migration Guide

When adding new tests:

1. **Ask**: Does this test need the actual `ht` binary?
   - **No** → `@pytest.mark.sdist`
   - **Yes** → `@pytest.mark.wheel`

2. **Place** the test in the appropriate functional directory:
   - Core functionality → `tests/lib_tests/`
   - Python-specific → `tests/py_unit_tests/`
   - CLI behavior → `tests/cli_tests/`

3. **Run** the test in its intended environment to verify it works

This strategy gives us the best of both worlds: lightning-fast unit tests for rapid development and comprehensive integration tests that verify real-world behavior.