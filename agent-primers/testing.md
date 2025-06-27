# Contributing to htty

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
nix develop .#pytest-wheel --command pytest tests/lib_tests/test_htty.py -v -s
```

### Environment-Specific Testing

We now use **pytest marks** to map tests to appropriate environments:

```bash
# Fast unit tests (Python-only, 3s builds)
nix develop .#pytest-sdist --command pytest -vs -m sdist

# Integration tests (with ht binary, 22s builds)  
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

See `agent-primers/pytest.md` for complete details on our pytest marks strategy.

### Why This Works

1. **No Stale Code**: Every test run rebuilds the environment from scratch
2. **Testing Reality**: You test the exact same `htty-pylib` package that users receive  
3. **Immediate Feedback**: Code changes in Rust (`src/rust/`) or Python (`src/python/`) are reflected instantly
4. **Dependency Isolation**: Test dependencies (pytest) are separate from the library being tested

### The Two-Environment Architecture

- **`htty-pylib`**: The exact Python environment users get when they install htty
- **`test-deps-only`**: Pytest and testing tools, added on top via uv2nix
- **Combined**: PYTHONPATH makes both available, with htty taking priority

This separation ensures you're always testing the real thing, not a development approximation.

### Development Commands

```bash
# Test specific module (wheel environment with ht binary)
nix develop .#pytest-wheel --command pytest tests/lib_tests/test_htty.py::test_hello_world -v -s

# Test all lib tests (wheel environment)
nix develop .#pytest-wheel --command pytest tests/lib_tests/ -v

# Fast unit tests (sdist environment, Python-only)
nix develop .#pytest-sdist --command pytest tests/py_unit_tests/ -v

# Use marks to run environment-appropriate tests
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-sdist --command pytest -vs -m sdist

# Interactive development (wheel environment)
nix develop .#pytest-wheel
# Now you have: pytest, python with htty, ht binary, and fresh code guaranteed
```

### Making Changes

1. **Edit code** in `src/rust/` (Rust) or `src/python/` (Python)
2. **Add to git**: `git add .` (Nix flakes need to see changes)
3. **Test immediately**: The test command will rebuild automatically

The build system handles:
- Rebuilding the Rust binary when `src/rust/` changes
- Rebuilding the Python wheel when `src/python/` changes  
- Creating fresh environments with updated code
- No manual build steps required

### Code Change → Rebuild Chain

When you modify source code, here's what gets rebuilt automatically:

- **Change `src/rust/*.rs`** → Rebuilds: ht → htty-wheel → htty-pylib → pytest environments
- **Change `src/python/**/*.py`** → Rebuilds: htty-wheel → htty-pylib → pytest environments  
- **Change `tests/pyproject.toml`** → Rebuilds: test dependencies in pytest environments

This ensures you always test fresh code and never encounter stale virtual environment issues.

## 🧪 Testing Guidelines

### Running Tests

```bash
# Quick unit test to verify your changes work (fast)
nix develop .#pytest-sdist --command pytest tests/py_unit_tests/test_args.py -v

# Integration test with real binary (slower but comprehensive)
nix develop .#pytest-wheel --command pytest tests/lib_tests/test_htty.py::test_hello_world_with_scrolling -v -s

# Run all tests in appropriate environments
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

### Writing Tests

- Put tests in `tests/lib_tests/` for Python library functionality
- Put tests in `tests/py_unit_tests/` for Python-only unit tests  
- Use pytest marks to declare environmental dependencies:
  - `@pytest.mark.wheel` for tests needing the ht binary
  - `@pytest.mark.sdist` for pure Python tests
- Use the existing test patterns with `htty.run()` and context managers
- Test files should be named `test_*.py`
- Import from `htty` normally - the environment provides everything needed

### Verifying Fresh Code

Code changes are immediately reflected due to Nix's dependency tracking. If you modify Python or Rust source, the next test run will automatically rebuild and use the updated code.

## 🛠️ Project Structure

```
src/rust/              # Rust source code (ht binary)
src/python/htty/       # Python library source
tests/lib_tests/       # Python library tests (integration)
tests/py_unit_tests/   # Pure Python unit tests
py-envs/lib/           # Production Python dependencies
py-envs/sdist/         # Python-only (no Rust) dependencies  
tests/                 # Test-only Python dependencies
nix/packages/          # Build system (see packaging.md)
nix/devshells/         # Development environments
```

## 🚫 What Not to Do

- **Don't use pip/uv/virtualenv** - The Nix workflow handles all dependencies
- **Don't manually build** - Let Nix handle builds automatically
- **Don't ignore test failures** - The fresh code guarantee means failures are real
- **Don't commit without testing** - Always run tests before committing
- **Don't mix environment types** - Use pytest marks to run tests in appropriate environments
