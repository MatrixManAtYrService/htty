# CI Workflow for htty Project

## Overview

This document describes the intended CI workflow for the htty project, which builds and publishes two separate packages to PyPI: `htty-core` (architecture-specific wheels) and `htty` (pure Python source distribution).

## Project Architecture Recap

The htty project uses a two-package distribution model:

- **htty-core**: Architecture-specific wheels containing the Rust `ht` binary and minimal Python bindings (built with maturin)
- **htty**: Pure Python source distribution that depends on `htty-core` and provides the high-level API

## CI Workflow Design

### Trigger Conditions

The CI workflow should trigger on:
- **Pull Requests**: For testing and validation
- **Push to main**: For integration testing
- **Tags**: For releases to PyPI

### Workflow Jobs

#### 1. **Lint and Analysis Job**
- **Runner**: `ubuntu-latest`
- **Purpose**: Fast feedback on code quality
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Run all analysis tools from `steps.sh`:
    - `nix run .#nix-analysis`
    - `nix run .#rust-analysis`
    - `nix run .#python-analysis`
    - `nix run .#generic-analysis`

#### 2. **Test Job**
- **Runner**: `ubuntu-latest`
- **Purpose**: Comprehensive testing across all environments
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Run the complete test suite from `steps.sh`:
    - Rust unit tests: `cargo test` in htty-core directory
    - Python tests across all environments:
      - `pytest -m empty` (pytest-empty devshell)
      - `pytest tests/lib_tests/test_htty_core.py` (pytest-core devshell)
      - `pytest -m wheel` (pytest-wheel devshell)
      - `pytest -m sdist` (pytest-sdist devshell)
      - `pytest -m htty` (pytest-htty devshell)
      - `pytest -m cli` (pytest-cli devshell)
  - Generate documentation: `nix run .#python-docs`

#### 3. **Build Wheels Job** (Matrix Strategy)
- **Purpose**: Build htty-core wheels for multiple architectures
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
  - Setup cross-compilation tooling (following maturin best practices):
    - **Option 1 (Recommended)**: Use maturin-action with Docker manylinux images
    - **Option 2**: Use Zig cross-compilation (`maturin build --zig`)
    - **Option 3**: Manual cross-toolchain setup (QEMU + GCC for aarch64-linux)
  - Setup Nix with caching
  - Build htty-core wheel using modified `htty-core-wheel.nix`
  - Test wheel installation and functionality (native builds only)
  - Upload wheel as artifact

#### 4. **Publish to PyPI Job**
- **Runner**: `ubuntu-latest`
- **Dependencies**: Requires successful completion of all build-wheels jobs
- **Environment**: `release` (for trusted publishing)
- **Permissions**: `id-token: write` (for OIDC trusted publishing)
- **Steps**:
  - Checkout code
  - Setup Nix with caching
  - Download all wheel artifacts from build-wheels jobs
  - Build htty source distribution: `nix build .#htty-sdist`
  - Verify all packages are present (wheels + sdist)
  - Publish to PyPI using `pypa/gh-action-pypi-publish@release/v1`
  - Support dry-run mode for testing

### Cross-Compilation Requirements

#### Current State
The existing `nix/packages/htty-core-wheel.nix` only supports native compilation. It needs to be enhanced to support cross-compilation for `aarch64-linux` targets.

#### Required Changes to `htty-core-wheel.nix`

1. **Accept target system parameter**:
   ```nix
   { inputs, pkgs, targetSystem ? null, ... }:
   ```

2. **Configure cross-compilation toolchain**:
   - Detect when `targetSystem` is different from `pkgs.system`
   - Set up appropriate Rust target and linker configuration
   - Configure Cargo for cross-compilation

3. **Handle target-specific dependencies**:
   - Ensure libc compatibility for Linux ARM64
   - Configure maturin for cross-compilation
   - Set appropriate wheel tags for target platform

4. **Environment variables for cross-compilation**:
   ```nix
   buildPhase = ''
     ${if targetSystem == "aarch64-linux" && pkgs.system == "x86_64-linux" then ''
       export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
       export CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc
       export CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++
       export AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar
       export STRIP_aarch64_unknown_linux_gnu=aarch64-linux-gnu-strip
     '' else ""}

     cargo build --release --bin ht ${if targetSystem != null then "--target ${targetSystem}" else ""}
     maturin build --release --out dist/ ${if targetSystem != null then "--target ${targetSystem}" else ""}
   '';
   ```

### CI Infrastructure

#### Nix Setup and Caching
- Use `nixbuild/nix-quick-install-action@v30` for Nix installation
- Use `nix-community/cache-nix-action@v6` for Nix store caching
- Cache key: `nix-store-${{ runner.os }}-${{ hashFiles('**/flake.lock') }}`
- Garbage collection: Keep store under 8GB before caching

#### Artifact Management
- Upload each wheel with platform-specific artifact names
- Merge all wheels in the publish job
- Include source distribution alongside wheels
- Verify package completeness before publishing

### Release Process

#### Version Management
- Versions are managed in `htty-core/Cargo.toml` and `htty/pyproject.toml`
- Both packages should maintain synchronized versions
- CI should validate version consistency across packages

#### Publishing Strategy
- **htty-core**: Publish architecture-specific wheels for each supported platform
- **htty**: Publish single source distribution that depends on htty-core
- Use PyPI's trusted publishing with OIDC for secure, keyless publishing

#### Supported Platforms
Following the same strategy as polars and other Rust-based Python packages:
- **Linux**: x86_64, aarch64
- **macOS**: x86_64 (Intel), aarch64 (Apple Silicon)
- **Windows**: Not initially supported (can be added later)

### Security and Best Practices

#### Trusted Publishing
- Use PyPI's trusted publishing instead of API tokens
- Configure GitHub repository as trusted publisher in PyPI
- Use `id-token: write` permission for OIDC authentication

#### Artifact Verification
- Verify wheel naming conventions match expected patterns
- Test wheel installation on native platforms before publishing
- Validate metadata consistency across packages

#### Secrets Management
- No API keys or tokens stored in repository
- All authentication handled via OIDC trusted publishing
- Cross-compilation tooling installed via package managers

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

## Implementation Plan

### Phase 1: Cross-Compilation Setup
1. Modify `nix/packages/htty-core-wheel.nix` to support cross-compilation
2. Test cross-compilation locally for aarch64-linux target
3. Validate cross-compiled wheels on actual ARM64 hardware

### Phase 2: Version Management System
1. Create `nix/lib/version.nix` as single source of truth for version information
   - Store major, minor, patch versions as separate attributes
   - Include git SHA from `git rev-parse HEAD`
   - Synthesize full version string (major.minor.patch)
2. Enhance `nix/packages/generic-analysis.nix` to propagate version updates
   - Update `htty-core/Cargo.toml`
   - Update `htty/pyproject.toml` 
   - Update any other files that reference version
   - Use cog templating to reference version environment variables
3. Add `--version` flag support to all binaries
   - `ht` binary: Print version and git SHA
   - `htty` command: Print version and git SHA  
   - `htty_core` module: Print version and git SHA
4. Create `nix run .#version-bump` script for version management
   - Support `--patch`, `--minor`, `--major` flags
   - Increment version in `version.nix`
   - Run `generic-analysis` to propagate changes
   - Automatically update all dependent files

### Phase 3: Basic CI Workflow
1. Create `.github/workflows/test.yml` for lint and test jobs
2. Create `.github/actions/setup-nix/action.yml` for reusable Nix setup
3. Test workflow on pull requests

### Phase 4: Release Workflow
1. Create `.github/workflows/release.yml` for wheel building and publishing
2. Configure PyPI trusted publishing
3. Test with dry-run releases

### Phase 5: Optimization and Enhancement
1. Add performance monitoring and caching optimizations
2. Add additional platforms if needed
3. Integrate additional quality gates

This workflow design ensures reliable, fast CI with comprehensive testing while supporting the project's unique two-package architecture and Nix-based build system.
