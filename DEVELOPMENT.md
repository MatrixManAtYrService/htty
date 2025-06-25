## Quick Start Guide - htty Python Development

### Current Working State (June 2025)

The htty Python bindings are **functional but incomplete**. Here's how to resume development:

### 1. Build & Test (Verified Working)

```bash
cd /Users/matt/src/ht

# Build the Rust binary
nix build .#htty --print-out-paths
# Note the output path, e.g. /nix/store/...-htty-0.3.0

# Build Python bindings in dev environment  
nix develop --command bash -c '
  python -m venv .venv
  source .venv/bin/activate
  PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --features python
'

# Test basic functionality
export PATH="/nix/store/kgajbdjcz6sxnj2hdlvg833158i0h8w4-htty-0.3.0/bin:$PATH"  # Use actual path
source .venv/bin/activate
python test_basic.py  # Should show ✅ for basic tests
```

### 2. What's Working

- ✅ `import htty` 
- ✅ `htty.Press.ENTER`, `htty.Press.TAB`, etc.
- ✅ `htty.run(["echo", "test"])`
- ✅ `with htty.ht_process(["vim"]) as proc:`
- ✅ `proc.send_keys(["hello", htty.Press.ENTER])`
- ⚠️ `proc.snapshot()` (exists but times out)

### 3. What Needs Fixing

Priority issues to tackle next:

1. **Snapshot Timing**: Debug why `proc.snapshot()` times out on simple commands
2. **Missing Methods**: Add to Python API:
   - `subprocess_controller.wait()`
   - `get_output()` for events
   - `terminate()` cleanup
3. **Test Suite**: Get `/Users/matt/src/htty/tests/test_ht_util.py` passing

### 4. Key Files

- `src/python.rs` - Main Python bindings (PyO3)
- `python/htty/__init__.py` - Python API surface
- `test_basic.py` - Simple working tests
- `/Users/matt/src/htty/tests/test_ht_util.py` - Target test suite

### 5. Blueprint Integration (Optional)

The flake works with basic structure, but could be upgraded to use blueprint pattern like `/Users/matt/src/htty/flake.nix` for consistency.

The foundation is solid - focus on completing the Python API to match test expectations!
