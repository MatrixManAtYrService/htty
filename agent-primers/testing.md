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

We use **pytest marks** to map tests to appropriate environments:

```bash
# Fast unit tests (Python-only, 3s builds)
nix develop .#pytest-sdist --command pytest -vs -m sdist

# Integration tests (with ht binary, 22s builds)  
nix develop .#pytest-wheel --command pytest -vs -m wheel

# Pure pytest environment (no htty packages)
nix develop .#pytest-empty --command pytest tests/external_tests/ -v
```

See `agent-primers/pytest.md` for complete details on our pytest marks strategy.

### Available Development Environments

We have four specialized pytest environments, each designed for specific testing scenarios:

#### pytest-empty
- **Purpose**: Pure pytest testing with no htty packages
- **Use case**: External integration tests, testing nix package access, baseline verification
- **Contains**: Only pytest and test dependencies
- **No htty**: Neither htty Python module nor ht binary
- **Test restriction**: Use `tests/env_tests/` only to avoid import failures

#### pytest-sdist  
- **Purpose**: Python-only unit testing with mocked binaries
- **Use case**: Fast iteration on Python logic
- **Contains**: htty Python-only package (hatchling build)
- **No binary**: ht binary is not available (intentional)
- **Test suites**: Can run all test suites

#### pytest-wheel
- **Purpose**: Full integration testing with real binary
- **Use case**: End-to-end workflows and binary integration
- **Contains**: Complete htty wheel with Rust binary + testVim
- **Full environment**: Both Python module and ht binary available
- **Test suites**: Can run all test suites

#### pytest-cli
- **Purpose**: CLI-only testing without Python module
- **Use case**: Testing CLI tools in isolation
- **Contains**: Both `ht` and `htty` commands via htty-cli package
- **No Python**: htty Python module is not available (intentional)
- **Test restriction**: Use `tests/cli_tests/` and `tests/env_tests/` only to avoid import failures

### Why This Works

1. **No Stale Code**: Every test run rebuilds the environment from scratch
2. **Testing Reality**: You test the exact same packages that users receive  
3. **Immediate Feedback**: Code changes in Rust (`src/rust/`) or Python (`src/python/`) are reflected instantly
4. **Dependency Isolation**: Test dependencies (pytest) are separate from the library being tested
5. **Shared Function**: All environments use `makePytestShell` for consistency

### The Build Architecture

All pytest environments use a shared function `makePytestShell` from `nix/lib/pytest-shell.nix`:

- **pytest-empty**: `makePytestShell { packages = []; }`
- **pytest-sdist**: `makePytestShell { packages = [htty-py-sdist]; }`  
- **pytest-wheel**: `makePytestShell { packages = [htty-pylib]; extraBuildInputs = [testVim]; }`

This ensures consistent test environment setup while allowing environment-specific customization.

### Development Commands

```bash
# Test specific module (wheel environment with ht binary)
nix develop .#pytest-wheel --command pytest tests/lib_tests/test_htty.py::test_hello_world -v -s

# Test all lib tests (wheel environment)
nix develop .#pytest-wheel --command pytest tests/lib_tests/ -v

# Fast unit tests (sdist environment, Python-only)
nix develop .#pytest-sdist --command pytest tests/py_unit_tests/ -v

# External integration tests (empty environment)
nix develop .#pytest-empty --command pytest tests/external_tests/ -v

# Environment verification tests (IMPORTANT: match environment to mark)
nix develop .#pytest-empty --command pytest -vs -m empty tests/env_tests/
nix develop .#pytest-cli --command pytest -vs -m cli tests/cli_tests/ tests/env_tests/
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-wheel --command pytest -vs -m wheel

# Interactive development (wheel environment)
nix develop .#pytest-wheel
# Now you have: pytest, python with htty, ht binary, testVim, and fresh code guaranteed
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

# External integration tests (verify nix package access)
nix develop .#pytest-empty --command pytest tests/external_tests/ -v

# Run all tests in appropriate environments
nix develop .#pytest-wheel --command pytest -vs -m wheel
nix develop .#pytest-sdist --command pytest -vs -m sdist
```

### Environment Testing

**IMPORTANT**: Always match the environment with its corresponding pytest mark to avoid import failures:

```bash
# Environment verification tests - match environment to mark
nix develop .#pytest-empty --command pytest -vs -m empty tests/env_tests/
nix develop .#pytest-cli --command pytest -vs -m cli tests/cli_tests/ tests/env_tests/
nix develop .#pytest-sdist --command pytest -vs -m sdist
nix develop .#pytest-wheel --command pytest -vs -m wheel
```

**Why restrict test suites?** Some environments lack Python setup (like `pytest-empty` and `pytest-cli`), so running tests that import htty in these environments will fail. The marks ensure tests only run in compatible environments:

- **`pytest-empty`**: No htty packages - restrict to `tests/env_tests/` to avoid import failures
- **`pytest-cli`**: CLI tools only, no Python htty - restrict to `tests/cli_tests/` and `tests/env_tests/`  
- **`pytest-sdist`**: Python htty only - can run all test suites
- **`pytest-wheel`**: Full environment - can run all test suites

### Writing Tests

- Put tests in `tests/lib_tests/` for Python library functionality
- Put tests in `tests/py_unit_tests/` for Python-only unit tests  
- Put tests in `tests/external_tests/` for nix package integration tests
- Put tests in `tests/env_tests/` for environment verification tests
- Put tests in `tests/cli_tests/` for CLI-only functionality tests
- Use pytest marks to declare environmental dependencies:
  - `@pytest.mark.wheel` for tests needing the ht binary and Python module
  - `@pytest.mark.sdist` for pure Python tests (no binary)
  - `@pytest.mark.empty` for tests verifying absence of htty packages
  - `@pytest.mark.cli` for tests needing CLI tools but no Python module
- Use the existing test patterns with `htty.run()` and context managers
- Test files should be named `test_*.py`
- Import from `htty` normally - the environment provides everything needed

**CRITICAL**: Always match environment with pytest mark to avoid import failures. For example, don't run `@pytest.mark.wheel` tests in `#pytest-empty` environment.

### External Integration Tests

The `tests/external_tests/` directory contains tests that verify htty packages work correctly when accessed via `nix shell`:

- Tests use `subprocess` to run `nix shell .#htty-pylib --ignore-environment`
- Verifies both Python import and binary access work in isolation
- Ensures proper package configuration for end users
- Run in pytest-empty environment to avoid dependency conflicts

### Verifying Fresh Code

Code changes are immediately reflected due to Nix's dependency tracking. If you modify Python or Rust source, the next test run will automatically rebuild and use the updated code.

## 🛠️ Project Structure

```
src/rust/              # Rust source code (ht binary)
src/python/htty/       # Python library source
tests/lib_tests/       # Python library tests (integration)
tests/py_unit_tests/   # Pure Python unit tests
tests/external_tests/  # External nix package integration tests
tests/env_tests/       # Environment verification tests
tests/cli_tests/       # CLI-only functionality tests (if exists)
py-envs/lib/           # Production Python dependencies
py-envs/sdist/         # Python-only (no Rust) dependencies  
tests/                 # Test-only Python dependencies
nix/packages/          # Build system (see packaging.md)
nix/devshells/         # Development environments
nix/lib/pytest-shell.nix  # Shared pytest environment function
```

## 🚫 What Not to Do

- **Don't use pip/uv/virtualenv** - The Nix workflow handles all dependencies
- **Don't manually build** - Let Nix handle builds automatically
- **Don't ignore test failures** - The fresh code guarantee means failures are real
- **Don't commit without testing** - Always run tests before committing
- **Don't mix environment types** - Use pytest marks to run tests in appropriate environments
