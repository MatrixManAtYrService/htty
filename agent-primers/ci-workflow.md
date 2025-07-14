# CI Workflow for htty Project

## Overview

This document describes the implemented CI workflow for the htty project, which builds and publishes two separate packages to PyPI: `htty-core` (architecture-specific wheels) and `htty` (pure Python source distribution).

## Project Architecture Recap

The htty project uses a two-package distribution model:

- **htty-core**: Architecture-specific wheels containing the Rust `ht` binary and minimal Python bindings (built with maturin)
- **htty**: Pure Python source distribution that depends on `htty-core` and provides the high-level API

## CI Workflow Implementation

### Implemented Files

The CI workflow is implemented through these GitHub Actions files:
- `.github/actions/setup-nix/action.yml` - Reusable Nix setup with caching
- `.github/workflows/test.yml` - Test and analysis workflow
- `.github/workflows/release.yml` - Release and publishing workflow

### Trigger Conditions

The CI workflows trigger on:
- **Pull Requests**: For testing and validation (test.yml)
- **Push to main**: For integration testing (test.yml)
- **Tags**: For releases to PyPI (release.yml)
- **Manual dispatch**: With dry-run option (release.yml)

### Workflow Jobs

#### 1. **Lint and Analysis Job** (Implemented)
- **Runner**: `ubuntu-latest`
- **Purpose**: Fast feedback on code quality
- **File**: `.github/workflows/test.yml`
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Run all analysis tools from `steps.sh`:
    - `nix run .#codegen`
    - `nix run .#nix-analysis`
    - `nix run .#rust-analysis`
    - `nix run .#python-analysis`

#### 2. **Test Job** (Implemented)
- **Runner**: `ubuntu-latest`
- **Purpose**: Comprehensive testing across all environments
- **File**: `.github/workflows/test.yml`
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Run the complete test suite from `steps.sh`:
    - Code generation: `nix run .#codegen`
    - Analysis: `nix run .#nix-analysis`, `nix run .#rust-analysis`, `nix run .#python-analysis`
    - Rust unit tests: `cargo test` in htty-core directory
    - Python tests across all environments:
      - `pytest -m empty` (pytest-empty devshell)
      - `pytest tests/lib_tests/test_htty_core.py` (pytest-core devshell)
      - `pytest -m wheel` (pytest-wheel devshell)
      - `pytest -m sdist` (pytest-sdist devshell)
      - `pytest -m htty` (pytest-htty devshell)
      - `pytest -m cli` (pytest-cli devshell)
  - Generate documentation: `nix run .#python-docs`

#### 3. **Build htty-core Wheels Job** (Matrix Strategy) (Implemented)
- **Purpose**: Build htty-core wheels for multiple architectures
- **File**: `.github/workflows/release.yml` (job: `build-htty-core-wheels`)
- **Matrix Dimensions**:
  ```yaml
  strategy:
    fail-fast: false
    matrix:
      include:
        # Linux builds
        - os: ubuntu-latest
          system: x86_64-linux
          build_type: native
        - os: ubuntu-latest
          system: aarch64-linux
          build_type: cross-compiled

        # macOS builds
        - os: macos-13  # Intel
          system: x86_64-darwin
          build_type: native
        - os: macos-latest  # ARM64
          system: aarch64-darwin
          build_type: native
  ```

- **Steps for Each Matrix Job**:
  - Checkout code
  - Setup Nix with caching
  - Build htty-core wheel using `htty-core-wheel.nix` with cross-compilation support
  - Uses maturin `--zig` cross-compilation (already implemented in `htty-core-wheel.nix`)
  - Test wheel installation and functionality (native builds only)
  - Upload wheel as artifact

#### 4. **Build htty Source Distribution Job** (Implemented)
- **Purpose**: Build htty pure Python source distribution
- **File**: `.github/workflows/release.yml` (job: `build-htty-sdist`)
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Build htty source distribution: `nix build .#htty-sdist`
  - Upload source distribution as artifact

#### 5. **Publish to PyPI Job** (Implemented)
- **Runner**: `ubuntu-latest`
- **File**: `.github/workflows/release.yml` (job: `publish-to-pypi`)
- **Dependencies**: Requires successful completion of both `build-htty-core-wheels` and `build-htty-sdist` jobs
- **Environment**: `release` (for trusted publishing)
- **Permissions**: `id-token: write` (for OIDC trusted publishing)
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Download all htty-core wheel artifacts from matrix builds
  - Download htty source distribution artifact
  - Verify all packages are present (4 wheels + 1 sdist)
  - Publish to PyPI using `pypa/gh-action-pypi-publish@release/v1`
  - Support dry-run mode for testing

### Cross-Compilation Implementation

#### Current State (Implemented)
The `nix/packages/htty-core-wheel.nix` has been enhanced to support cross-compilation for all target architectures using maturin best practices.

#### Implemented Features in `htty-core-wheel.nix`

1. **Target system parameter** (✅ Implemented):
   ```nix
   { inputs, pkgs, targetSystem ? null, ... }:
   ```

2. **Cross-compilation detection** (✅ Implemented):
   - Detects when `targetSystem` is different from `pkgs.stdenv.hostPlatform.system`
   - Sets up appropriate Rust target mapping
   - Configures Rust toolchain with required targets

3. **Maturin with Zig cross-compilation** (✅ Implemented):
   - Uses `maturin build --zig` for cross-compilation (following maturin best practices)
   - Automatic cross-compilation toolchain via Zig
   - No manual GCC/linker configuration needed

4. **Target platform mappings** (✅ Implemented):
   ```nix
   rustTargetMap = {
     "aarch64-linux" = "aarch64-unknown-linux-gnu";
     "x86_64-linux" = "x86_64-unknown-linux-gnu";
     "aarch64-darwin" = "aarch64-apple-darwin";
     "x86_64-darwin" = "x86_64-apple-darwin";
   };
   ```

### CI Infrastructure (Implemented)

#### Nix Setup and Caching (✅ Implemented)
- **File**: `.github/actions/setup-nix/action.yml`
- Uses `nixbuild/nix-quick-install-action@v30` for Nix installation
- Uses `nix-community/cache-nix-action@v6` for Nix store caching
- Cache key: `nix-store-${{ runner.os }}-${{ hashFiles('**/flake.lock') }}`
- Garbage collection: Keep store under 8GB before caching

#### Artifact Management (✅ Implemented)
- Upload each htty-core wheel with platform-specific artifact names (`htty-core-wheel-{system}`)
- Upload htty source distribution as separate artifact (`htty-sdist`)
- Merge all artifacts in the publish job using `merge-multiple: true`
- Verify package completeness before publishing (4 wheels + 1 sdist expected)

### Release Process

#### Version Management
- Versions are managed in `htty-core/Cargo.toml` and `htty/pyproject.toml`
- Both packages should maintain synchronized versions
- CI should validate version consistency across packages

#### Publishing Strategy (✅ Implemented)
- **htty-core**: Publish architecture-specific wheels for each supported platform (4 wheels)
- **htty**: Publish single source distribution that depends on htty-core (1 sdist)
- Uses PyPI's trusted publishing with OIDC for secure, keyless publishing
- Supports dry-run mode for testing releases

#### Supported Platforms (✅ Implemented)
Following the same strategy as polars and other Rust-based Python packages:
- **Linux**: x86_64, aarch64 (cross-compiled with maturin --zig)
- **macOS**: x86_64 (Intel), aarch64 (Apple Silicon)
- **Windows**: Not currently supported (can be added later)

### Security and Best Practices (✅ Implemented)

#### Trusted Publishing (✅ Implemented)
- Uses PyPI's trusted publishing instead of API tokens
- Requires GitHub repository to be configured as trusted publisher in PyPI
- Uses `id-token: write` permission for OIDC authentication
- Environment: `release` for additional protection

#### Artifact Verification (✅ Implemented)
- Verifies expected number of packages (4 wheels + 1 sdist)
- Tests wheel installation on native platforms before publishing
- Shows package details and sizes before publishing
- Validates artifact completeness across matrix builds

#### Secrets Management (✅ Implemented)
- No API keys or tokens stored in repository
- All authentication handled via OIDC trusted publishing
- Cross-compilation tooling (Zig) installed via Nix packages

### Future Enhancements

#### Additional Platforms
- **Windows support**: Could be added later with `windows-latest` runners
- **Additional architectures**: RISC-V, PowerPC if needed

#### Performance Optimizations
- **Parallel testing**: Run test jobs in parallel with build jobs
- **Conditional builds**: Only build changed packages
- **Incremental builds**: Cache Rust compilation artifacts

#### Quality Gates
- **Coverage reporting**: Integrate with codecov or similar
- **Benchmark tracking**: Monitor performance regressions
- **Security scanning**: Integrate vulnerability scanning tools

## Implementation Status

### ✅ Completed Implementation

All major phases of the CI workflow have been successfully implemented:

#### Phase 1: Cross-Compilation Setup (✅ Complete)
- ✅ Enhanced `nix/packages/htty-core-wheel.nix` with cross-compilation support
- ✅ Implemented maturin `--zig` cross-compilation approach
- ✅ Support for all target architectures (x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin)

#### Phase 3: Basic CI Workflow (✅ Complete)
- ✅ Created `.github/workflows/test.yml` for lint and test jobs
- ✅ Created `.github/actions/setup-nix/action.yml` for reusable Nix setup
- ✅ Comprehensive testing across all pytest environments
- ✅ All analysis tools from `steps.sh` integrated

#### Phase 4: Release Workflow (✅ Complete)
- ✅ Created `.github/workflows/release.yml` for wheel building and publishing
- ✅ Matrix builds for all supported platforms
- ✅ Two-package architecture support (htty-core wheels + htty sdist)
- ✅ PyPI trusted publishing configuration
- ✅ Dry-run support for testing releases

### 🚧 Remaining Work

#### Phase 2: Version Management System (Future Enhancement)
- Create `nix/lib/version.nix` as single source of truth for version information
- Enhance `nix/packages/generic-analysis.nix` to propagate version updates
- Add `--version` flag support to all binaries
- Create `nix run .#version-bump` script for version management

#### Phase 5: Additional Optimizations (Future Enhancement)
- Performance monitoring and caching optimizations
- Additional platforms (Windows support)
- Additional quality gates (coverage, benchmarks, security scanning)

### 🎯 Current Status

The CI workflow is **fully functional and ready for production use**. It provides:

- ✅ **Comprehensive testing** across all environments on every PR
- ✅ **Multi-architecture builds** with cross-compilation
- ✅ **Secure PyPI publishing** with trusted publishing
- ✅ **Two-package distribution** (htty-core + htty)
- ✅ **Dry-run capabilities** for testing releases

The implementation follows maturin best practices and mirrors successful Rust-Python projects like polars, ensuring reliable and efficient CI/CD for the htty project.
