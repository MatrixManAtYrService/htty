# Packaging Architecture

## 🏗️ Build System Overview

This project uses a sophisticated Nix-based build system that creates a DAG (Directed Acyclic Graph) of packages. Each package serves different use cases, and users can build any package along this chain depending on their needs.

## 📊 Dependency Structure

### Nix Packages

**htty-core-wheel.nix**
- Source: `./htty-core/` (Rust + Python source)
`htty-core` is the part that wraps `ht` (which is written in rust).
It provides a wheel which is architecture-specific.

**htty-core-env.nix**
- Dependencies: `htty-core-wheel.nix`
`htty-core-wheel` is for getting a wheel that we can then hand off to pypi.
This package gives you an environment where that wheel is already installed.

**htty-sdist.nix**
- Source: `./htty/` (Python wrapper source)

`htty` depends on `htty-core` but it is itself a pure python package.
As such, we can send it to pypi as a non-architecture-specific sdist.

**htty-env.nix**
- Source: `./htty/` (Python wrapper source)
- Dependencies: `htty-core-wheel.nix`

Much like how `htty-core-env` is an environment with `htty-core-wheel` already
installed, `htty-env` is not what we send to pypi but instead what you get when
you install it.

As such, it's the full experience, with both `htty` importable as a python package, and `htty` runnable as a shell command.

**htty-cli.nix**
- Dependencies: `htty.nix`

This packages is for users that only want to interact with `htty` via the
command line.  It does not set the environment up for `import htty` via python.

It's helpful to distinguish this case because otherwise users might install
`htty` for CLI use and then be suprised when something about their python
environment has changed (suprising dependency versions might get used due to
alterations to `PYTHONPATH`).

**Analysis packages** (independent)
- `nix-analysis.nix`
- `rust-analysis.nix`
- `python-analysis.nix`
- `codegen.nix`

### Nix Devshells

**default.nix**
- Dependencies: TBD

**pytest-empty.nix**
- Dependencies: none (testing nix functionality)

**pytest-core.nix**
- Dependencies: `htty-core-env.nix`

**pytest-cli.nix**
- Dependencies: `htty-cli.nix`

**pytest-full.nix**
- Dependencies: `htty.nix`

## 📦 Package & Devshell Reference

| Name | Type | Purpose | Command |
|------|------|---------|--------|
| `htty-core-wheel` | Package | Maturin-built wheel with Rust binary + Python bindings | `nix build .#htty-core-wheel` |
| `htty-core-env` | Package | Minimal Python environment with just htty_core | `nix shell .#htty-core-env` |
| `htty` | Package | Complete Python environment (htty + htty_core + deps) | `nix shell .#htty` |
| `htty-cli` | Package | CLI wrapper without Python environment pollution | Include in devshell `buildInputs` |
| `nix-analysis` | Package | Nix code analysis (deadnix, nixpkgs-fmt, statix) | `nix run .#nix-analysis` |
| `rust-analysis` | Package | Rust code analysis (clippy) | `nix run .#rust-analysis` |
| `python-analysis` | Package | Python code analysis (ruff, pyright) | `nix run .#python-analysis` |
| `codegen` | Package | Code generation (cog, trim-whitespace) | `nix run .#codegen` |
| `default` | Devshell | Default development environment | `nix develop` |
| `pytest-empty` | Devshell | Testing environment with no htty packages | `nix develop .#pytest-empty` |
| `pytest-core` | Devshell | Testing environment with htty-core only | `nix develop .#pytest-core` |
| `pytest-cli` | Devshell | Testing environment with CLI tools | `nix develop .#pytest-cli` |
| `pytest-full` | Devshell | Testing environment with complete htty | `nix develop .#pytest-full` |

## 🔄 Dependency Resolution

### uv2nix Integration

The project uses `uv2nix` for Python dependency management:

1. **`htty/`** - Complete htty package dependencies
   - `pyproject.toml` defines htty + runtime deps
   - `uv.lock` pins exact versions
   - Used by `htty.nix`

2. **`tests/`** - Test dependencies
   - `pyproject.toml` defines pytest + test tools
   - `uv.lock` pins exact versions
   - Used by `pytest-wheel` devshell

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

- **`htty-core/` changes** → `htty-core-wheel.nix` → `htty-core-env.nix`, `htty.nix` → `htty-cli.nix`
- **`htty/` changes** → `htty.nix` → `htty-cli.nix`
- **`htty/uv.lock` changes** → `htty.nix` → `htty-cli.nix`

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

This architecture ensures clean separation of concerns while providing maximum flexibility for different use cases.
