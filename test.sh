#!/usr/bin/env bash
set -euox pipefail

# Check if nom (nix output monitor) is available
if command -v nom &> /dev/null; then
    NIX_CMD="nom"
else
    NIX_CMD="nix"
    echo "🔍 Using nix (nom not found)"
    echo "try: `nix develop --command ./test.sh` for more transparent nix output"

fi

# Code analysis tools grouped by language
# These run deadnix, nixpkgs-fmt, statix, ruff-check, ruff-format, trim-whitespace and rust-clippy
nix run .#nix-analysis
nix run .#rust-analysis
nix run .#python-analysis
nix run .#generic-analysis

echo "✅ All fast analyzers passed! Running tests..."

# Tests below are organized from fastest to slowest
# Rust unit tests (JSON parsing, key handling, etc.)
$NIX_CMD develop . --command bash -c "cd htty-core && cargo test"

# Things that should be true even when nothing is installed
# e.g. nix-shell commands that reference this flake still work
$NIX_CMD develop .#pytest-empty --command pytest -m empty tests/env_tests/

# Tests that only need htty-core (Rust binary + minimal Python bindings)
$NIX_CMD develop .#pytest-core --command pytest -m core

# Tests that verify htty-core-wheel package produces correct Python wheel
$NIX_CMD develop .#pytest-wheel --command pytest -m wheel tests/env_tests/

# Tests that verify htty-sdist package produces correct source distribution
$NIX_CMD develop .#pytest-sdist --command pytest -m sdist tests/env_tests/

# Tests that verify htty package contains expected files and binaries
$NIX_CMD develop .#pytest-htty --command pytest -m htty tests/env_tests/

# This flake outputs a CLI package for users that just want to run commands
# but don't want to modify their python environment
$NIX_CMD develop .#pytest-cli --command pytest -m cli tests/env_tests/ tests/cli_tests

# Additional tests that need the complete environment (htty-core + htty wrapper)
# These are covered by the pytest-htty environment above, so this line is commented out
$NIX_CMD develop .#pytest-htty --command pytest -m htty
