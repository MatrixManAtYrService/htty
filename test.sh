#!/usr/bin/env bash
set -x

# Things that should be true even when nothing is installed
# e.g. nix-shell commands that reference this flake still work
nix develop .#pytest-empty --command pytest -m empty tests/env_tests/

# Tests that don't need the rust parts
nix develop .#pytest-sdist --command pytest -m sdist

# Tests that need both parts
nix develop .#pytest-wheel --command pytest -m wheel

# This flake outputs a CLI package for users that just want to run
# but don't want to modify their python environment
nix develop .#pytest-cli --command pytest -m cli tests/env_tests/ tests/cli_tests


# for more info, try running these like
# not like "... pytest -m ..."
# but like "... pytest -vs -m ..."
