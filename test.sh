#!/usr/bin/env bash

# Parse command line arguments
verbose=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            verbose=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--verbose]"
            echo "  --verbose  Enable verbose output for all tests and analyzers"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--verbose]"
            exit 1
            ;;
    esac
done

# Function to run nix commands with clear output
run_nix() {
    echo "💡 Running: $*"
    "$@"
}

# Function to run analyzer commands with optional verbose flag
run_analyzer() {
    if [ "$verbose" = "true" ]; then
        run_nix "$@" -v
    else
        run_nix "$@"
    fi
}

# Function to run pytest commands with optional verbose flags
run_pytest() {
    if [ "$verbose" = "true" ]; then
        # Insert -vs after pytest command
        local cmd=("$@")
        local new_cmd=()
        local pytest_found=false
        
        for arg in "${cmd[@]}"; do
            new_cmd+=("$arg")
            if [[ "$arg" == *"pytest" ]] && [ "$pytest_found" = "false" ]; then
                new_cmd+=("-vs")
                pytest_found=true
            fi
        done
        
        run_nix "${new_cmd[@]}"
    else
        run_nix "$@"
    fi
}

# Function to run cargo test with optional verbose flag
run_cargo_test() {
    if [ "$verbose" = "true" ]; then
        run_nix "$@" --verbose
    else
        run_nix "$@"
    fi
}

# Code analysis tools grouped by language
# These run deadnix, nixpkgs-fmt, statix, ruff-check, ruff-format, trim-whitespace and rust-clippy

# Track failures but don't exit immediately
failed_analyzers=()

if ! run_analyzer nix run .#nix-analysis; then
    failed_analyzers+=("nix-analysis")
fi

if ! run_analyzer nix run .#rust-analysis; then
    failed_analyzers+=("rust-analysis")
fi

if ! run_analyzer nix run .#python-analysis; then
    failed_analyzers+=("python-analysis")
fi

if ! run_analyzer nix run .#generic-analysis; then
    failed_analyzers+=("generic-analysis")
fi

if [ ${#failed_analyzers[@]} -ne 0 ]; then
    echo "❌ The following analyzers failed: ${failed_analyzers[*]}"
    exit 1
fi

echo "✅ All fast analyzers passed! Running tests..."

# Tests below are organized from fastest to slowest
# don't go on to the slow tests if the fast ones fail
set -e

# Rust unit tests (JSON parsing, key handling, etc.)
run_cargo_test nix develop . --command cargo test

# Things that should be true even when nothing is installed
# e.g. nix-shell commands that reference this flake still work
run_pytest nix develop .#pytest-empty --command pytest -m empty tests/env_tests/

# Tests that don't need the rust parts
run_pytest nix develop .#pytest-sdist --command pytest -m sdist

# Tests that need both parts
run_pytest nix develop .#pytest-wheel --command pytest -m wheel

# This flake outputs a CLI package for users that just want to run commands
# but don't want to modify their python environment
run_pytest nix develop .#pytest-cli --command pytest -m cli tests/env_tests/ tests/cli_tests


# for more info, try running these like
# not like "... pytest -m ..."
# but like "... pytest -vs -m ..."
