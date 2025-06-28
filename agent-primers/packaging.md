# Packaging Architecture

## 🏗️ Build System Overview

This project uses a sophisticated Nix-based build system that creates a DAG (Directed Acyclic Graph) of packages. Each package serves different use cases, and users can build any package along this chain depending on their needs.

## 📊 The Build DAG

```
Rust Source Code (src/rust/)
     ↓
┌────────────────┐
│     ht.nix     │ ← Pure Rust binary (ht command)
└────────────────┘
     ↓
┌────────────────┐
│ htty-wheel.nix │ ← Python wheel with Rust binary embedded
└────────────────┘
     ↓
┌────────────────┐
│ htty-pylib.nix │ ← Clean Python environment with htty library
└────────────────┘
     ↓                           ↓                    ↓
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│ htty-cli.nix   │   │ htty-test.nix  │   │htty-py-sdist.nix│ ← Hatchling Python-only
└────────────────┘   └────────────────┘   └────────────────┘
                          ↓                    ↓
                     ┌────────────────┐   ┌────────────────┐
                     │#pytest-wheel   │   │#pytest-sdist   │ ← Development environments
                     └────────────────┘   └────────────────┘
```

## 📦 Package Definitions

### 1. `ht.nix` - Pure Rust Binary

**Purpose:** The core Rust binary with no Python dependencies
**Location:** `nix/packages/ht.nix`
**Input:** `src/rust/` directory (Rust source code)
**Output:** `ht` binary

```bash
nix build .#ht
./result/bin/ht --help
```

**What it does:**
- Compiles Rust source with `cargo build --release --bin ht`
- Provides the core headless terminal functionality
- No Python features enabled
- Perfect for standalone CLI usage

**Technical details:**
- Uses `rustPlatform.buildRustPackage`
- Imports `Cargo.lock` for reproducible builds
- Includes platform-specific build inputs (libiconv, Foundation on macOS)

---

### 2. `htty-wheel.nix` - Python Wheel with Embedded Binary

**Purpose:** Python wheel containing both Python library and Rust binary
**Location:** `nix/packages/htty-wheel.nix`
**Input:** `src/rust/` directory + `src/python/` directory
**Output:** `.whl` file

```bash
nix build .#htty-wheel
ls ./result/*.whl
```

**What it does:**
- Uses `maturin build --release` to create Python wheel
- Embeds the Rust binary into the wheel via PyO3 bindings
- Creates the bridge between Rust and Python
- Used as input for downstream Python environments

**Technical details:**
- Uses maturin for Rust-Python integration
- Builds with PyO3 features enabled
- Creates wheel metadata for consumers
- Output includes `wheel-filename.txt` and `wheel-path.txt`

---

### 3. `htty-pylib.nix` - Clean Python Environment

**Purpose:** Production Python environment that users receive
**Location:** `nix/packages/htty-pylib.nix`
**Input:** `htty-wheel.nix` + `py-envs/lib/` directory
**Output:** Python virtual environment with htty installed

```bash
nix build .#htty-pylib
./result/bin/python -c "import htty; print('✅')"
```

**What it does:**
- Uses `uv2nix` to load `py-envs/lib/pyproject.toml` and `py-envs/lib/uv.lock`
- Creates Python package set with pyproject-nix
- Overrides the `htty` package to use our wheel instead of PyPI
- Creates clean virtual environment with htty + its dependencies
- **Includes CLI tools**: Provides both `ht` binary and `python -m htty` access
- **This is exactly what end users get**

**Dependencies specified in `py-envs/lib/pyproject.toml`:**
```toml
[project]
name = "htty-pylib-env"
dependencies = [
    "htty",        # ← Gets overridden to use our wheel
    "ansi2html",   # ← Runtime dependency
]
```

**Technical details:**
- Uses `uv2nix.lib.workspace.loadWorkspace`
- Creates overlay to replace htty with our wheel
- Uses `mkVirtualEnv` to create clean environment
- Leverages uv.lock for reproducible Python dependencies

---

### 4. `htty-cli.nix` - CLI Tools Package

**Purpose:** Both CLI commands without Python environment pollution
**Location:** `nix/packages/htty-cli.nix`
**Input:** `htty.nix` (for ht binary) + `htty-pylib.nix` (for htty CLI)
**Output:** `ht` and `htty` commands

```bash
nix build .#htty-cli
./result/bin/ht --help      # Rust binary
./result/bin/htty --help    # Python CLI wrapper
```

**What it does:**
- Builds the Rust binary separately (no Python features)
- Creates wrapper script for `htty` that calls `python -m htty` using htty-pylib
- Provides both CLI tools without exposing Python environment details
- Perfect for devshells where you want CLI tools but no Python in PATH

**Technical details:**
- Separate Rust build with `cargo build --release --bin ht`
- Wrapper script: `exec ${httyPylib}/bin/python -m htty "$@"`
- No Python dependencies in the resulting environment
- Clean separation of CLI and library concerns

---

### 5. `htty-test.nix` - Test Environment Package

**Purpose:** Combines htty-pylib with test tools for traditional testing
**Location:** `nix/packages/htty-test.nix`
**Input:** `htty-pylib.nix` + `tests/` directory
**Output:** Test environment with wrapper scripts

```bash
nix build .#htty-test
./result/bin/htty-test      # Basic functionality test
./result/bin/htty-pytest   # Pytest wrapper
```

**What it does:**
- Uses `uv2nix` to load `tests/pyproject.toml` and `tests/uv.lock`
- Creates test dependencies environment (pytest, etc.)
- Excludes htty from test deps (gets it from htty-pylib instead)
- Creates wrapper scripts that combine both environments via PYTHONPATH
- **Legacy approach** - the new pytest devshell is preferred

**Dependencies specified in `tests/pyproject.toml`:**
```toml
[project]
name = "htty-test-env"
dependencies = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    # htty is provided separately by htty-pylib input
]
```

**Technical details:**
- Uses `builtins.removeAttrs testWorkspace.deps.default [ "htty" ]`
- Creates wrapper scripts that set PYTHONPATH
- Combines environments without conflicts
- Provides `htty-test`, `htty-pytest`, `htty-test-python` commands

---

### 6. `htty-py-sdist.nix` - Pure Python Source Distribution

**Purpose:** Python-only package built with hatchling for unit testing
**Location:** `nix/packages/htty-py-sdist.nix`
**Input:** `src/python/` directory (Python source only)
**Output:** Python environment with htty but no ht binary

```bash
nix build .#htty-py-sdist
# Used internally by pytest-sdist devshell
```

**What it does:**
- Uses hatchling to create proper Python source distribution
- Contains only Python source code (no Rust binary)
- Perfect for unit testing in isolation
- Fast builds (~3s) since no Rust compilation needed

---

### 7. `#pytest-wheel` & `#pytest-sdist` - Development Shells

**Purpose:** Environment-specific development shells with pytest marks support
**Location:** `nix/devshells/pytest-wheel.nix` and `nix/devshells/pytest-sdist.nix`
**Input:** Different htty packages + test dependencies via uv2nix
**Output:** Interactive shells optimized for different test types

```bash
# Integration testing with ht binary (22s builds)
nix develop .#pytest-wheel
pytest -vs -m wheel  # Run wheel-marked tests

# Unit testing without binary (3s builds)
nix develop .#pytest-sdist
pytest -vs -m sdist  # Run sdist-marked tests
```

**What they do:**
- **pytest-wheel**: Uses `htty-pylib` (complete wheel with ht binary)
- **pytest-sdist**: Uses `htty-py-sdist` (Python-only source distribution)
- Both create separate `test-deps-only` environment via uv2nix from `tests/`
- Combine environments via PYTHONPATH in shell environment
- Rebuild appropriate packages when source code changes
- **No wrapper scripts** - direct tool access
- **Fresh code guarantee** - every entry rebuilds if needed
- **Pytest marks support** - tests declare their environmental needs

**Technical details:**
- Use `mkShell` with both environments in buildInputs
- Set PYTHONPATH in shellHook for proper precedence
- Include development tools (uv, ruff, nixpkgs-fmt, nil)
- Platform-specific dependencies (libiconv, Foundation on macOS)
- Support pytest marks: `@pytest.mark.wheel` and `@pytest.mark.sdist`

## 🔄 Dependency Resolution

### uv2nix Integration

The project uses `uv2nix` for Python dependency management:

1. **`py-envs/lib/`** - Production dependencies
   - `pyproject.toml` defines htty + runtime deps
   - `uv.lock` pins exact versions
   - Used by `htty-pylib.nix`

2. **`py-envs/sdist/`** - Python-only dependencies
   - `pyproject.toml` defines htty with hatchling backend (no Rust)
   - `uv.lock` pins exact versions
   - Used by `htty-py-sdist.nix`

3. **`tests/`** - Test dependencies
   - `pyproject.toml` defines pytest + test tools
   - `uv.lock` pins exact versions
   - Used by both `pytest-wheel` and `pytest-sdist` devshells

### Overlay System

Each package uses Nix overlays to customize the Python package set:

```nix
pythonSet = (pkgs.callPackage pyproject-nix.build.packages {
  python = pkgs.python3;
}).overrideScope (
  pkgs.lib.composeManyExtensions [
    pyproject-build-systems.overlays.default  # Build tools
    (workspace.mkPyprojectOverlay { ... })     # uv2nix dependencies
    customOverrides                            # Package-specific fixes
  ]
);
```

### Rebuild Triggers

The Nix dependency system automatically rebuilds packages when inputs change:

- **`src/rust/*.rs` changes** → `ht.nix` → `htty-wheel.nix` → `htty-pylib.nix` → pytest-wheel
- **`src/python/**/*.py` changes** → `htty-wheel.nix` → `htty-pylib.nix` → pytest-wheel, `htty-py-sdist.nix` → pytest-sdist
- **`py-envs/lib/uv.lock` changes** → `htty-pylib.nix` → pytest-wheel
- **`tests/uv.lock` changes** → both pytest environments
- **`py-envs/sdist/pyproject.toml` changes** → `htty-py-sdist.nix` → pytest-sdist

## 🎯 Design Principles

### 1. Separation of Concerns
- **CLI-only packages** don't include Python environments (preventing Python pollution)
- **Python packages** include CLI tools (giving Python users the full experience)
- **Test environments** separate from production environments

### 2. Fresh Code Guarantee
- Source changes trigger automatic rebuilds
- No stale virtual environments possible
- Development environment matches production

### 3. User Choice
- Users can build exactly what they need
- No forced dependencies or environment pollution
- Clear boundaries between package types

### 4. Reproducibility
- All dependencies pinned via uv.lock files
- Nix ensures bit-for-bit reproducible builds
- Same environment across all machines

## 🔧 Adding New Packages

To add a new package to the DAG:

1. **Create package definition** in `nix/packages/new-package.nix`
2. **Define inputs** from existing packages or source
3. **Specify build process** using appropriate Nix builders
4. **Add to blueprint** - Nix blueprint will discover it automatically
5. **Test the package** with `nix build .#new-package`

### Example Package Template

```nix
{ inputs, pkgs, ... }:

let
  # Define inputs
  someInput = inputs.self.packages.${pkgs.system}.some-dependency;

  # Package metadata
  version = "1.0.0";
in
pkgs.stdenv.mkDerivation {
  pname = "new-package";
  inherit version;

  # Define sources and dependencies
  src = ../..;
  buildInputs = [ someInput ];

  # Build process
  buildPhase = ''
    # Build steps
  '';

  installPhase = ''
    # Install steps
  '';

  meta = with pkgs.lib; {
    description = "Description of the package";
    license = licenses.mit;
  };
}
```

## 📋 Package Use Cases

| Package | Use Case | Command |
|---------|----------|---------|
| `ht` | Standalone Rust binary | `nix run .#ht` |
| `htty-wheel` | Python packaging integration | `nix build .#htty-wheel` |
| `htty-pylib` | Python development/production | `nix shell .#htty-pylib` |
| `htty-py-sdist` | Python-only unit testing | `nix build .#htty-py-sdist` |
| `htty-cli` | DevShell CLI tools | Include in `buildInputs` |
| `htty-test` | CI/testing (legacy) | `nix build .#htty-test` |
| `#pytest-wheel` | Integration test workflow | `nix develop .#pytest-wheel` |
| `#pytest-sdist` | Unit test workflow | `nix develop .#pytest-sdist` |

This architecture ensures clean separation of concerns while providing maximum flexibility for different use cases.
