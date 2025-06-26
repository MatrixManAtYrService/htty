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

### Code Change → Rebuild Chain

When you modify source code, here's what gets rebuilt automatically:

- **Change `src/*.rs`** → Rebuilds: htty → htty-wheel → htty-pylib → #pytest shell
- **Change `python/**/*.py`** → Rebuilds: htty-wheel → htty-pylib → #pytest shell  
- **Change `tests/pyproject.toml`** → Rebuilds: test dependencies in #pytest shell

This ensures you always test fresh code and never encounter stale virtual environment issues.

## 🧪 Testing Guidelines

### Running Tests

```bash
# Quick test to verify your changes work
nix develop .#pytest --command pytest tests/lib_tests/test_help_freshness.py -v

# Run all library tests
nix develop .#pytest --command pytest tests/lib_tests/ -v

# Run specific test with output
nix develop .#pytest --command pytest tests/lib_tests/test_htty.py::test_specific_function -v -s
```

### Writing Tests

- Put tests in `tests/lib_tests/` for Python library functionality
- Use the existing test patterns with `htty.ht_process()` context manager
- Test files should be named `test_*.py`
- Import from `htty` normally - the environment provides everything needed

### Verifying Fresh Code

The `test_help_freshness.py` tests verify that code changes are immediately reflected. If you modify the Rust CLI help text in `src/cli.rs`, the tests should detect the change immediately.

## 🛠️ Project Structure

```
src/                    # Rust source code (ht binary)
python/htty/           # Python library source
tests/lib_tests/       # Python library tests
pylib-env/             # Production Python dependencies
tests/                 # Test-only Python dependencies
nix/packages/          # Build system (see PACKAGING.md)
nix/devshells/         # Development environments
```

## 📝 Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your changes
3. **Make changes** in `src/` (Rust) or `python/` (Python)  
4. **Add files to git**: `git add .`
5. **Test your changes**: `nix develop .#pytest --command pytest tests/lib_tests/ -v`
6. **Commit and push** your changes
7. **Submit a pull request**

The CI system uses the same Nix-based workflow, so if tests pass locally, they should pass in CI.

## 🚫 What Not to Do

- **Don't use pip/uv/virtualenv** - The Nix workflow handles all dependencies
- **Don't manually build** - Let Nix handle builds automatically
- **Don't ignore test failures** - The fresh code guarantee means failures are real
- **Don't commit without testing** - Always run tests before committing

## ❓ Getting Help

- **Build issues**: Check that you've added files to git (`git add .`)
- **Test failures**: The fresh code guarantee means the failure is real - debug normally
- **Environment issues**: Try `nix develop .#pytest` and see what's available
- **Complex changes**: See [PACKAGING.md](PACKAGING.md) for build system details

The Nix-based workflow ensures that your development environment exactly matches what users get, making debugging and development more reliable.
