"""Test htty-sdist and htty packages for expected outputs"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.sdist
def test_htty_sdist_tgz_output():
    """Test that htty-sdist produces a .tar.gz file"""
    result = subprocess.run(
        ["nix", "build", ".#htty-sdist", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to build htty-sdist: {result.stderr}"

    output_path = result.stdout.strip()
    assert output_path, "No output path returned"

    # Check that the output contains a .tar.gz file
    tgz_files = list(Path(output_path).glob("*.tar.gz"))
    assert len(tgz_files) == 1, f"Expected exactly one .tar.gz file, found: {tgz_files}"

    # Check that it's named correctly
    tgz_file = tgz_files[0]
    assert "htty" in tgz_file.name, f"Expected htty in filename, got: {tgz_file.name}"
    assert "0.3.0" in tgz_file.name, f"Expected version in filename, got: {tgz_file.name}"


@pytest.mark.sdist
def test_htty_sdist_metadata_files():
    """Test that htty-sdist produces metadata files"""
    result = subprocess.run(
        ["nix", "build", ".#htty-sdist", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to build htty-sdist: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Check for metadata files
    assert (output_path / "sdist-filename.txt").exists(), "Missing sdist-filename.txt"
    assert (output_path / "sdist-path.txt").exists(), "Missing sdist-path.txt"


@pytest.mark.htty
def test_htty_cli_py_file():
    """Test that htty package contains cli.py in site-packages"""
    result = subprocess.run(
        ["nix", "build", ".#htty", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to build htty: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Check for cli.py in site-packages
    cli_py = output_path / "lib" / "python3.12" / "site-packages" / "htty" / "cli.py"
    assert cli_py.exists(), f"Missing cli.py at expected location: {cli_py}"


@pytest.mark.htty
def test_htty_ht_binary():
    """Test that htty package contains ht binary"""
    result = subprocess.run(
        ["nix", "build", ".#htty", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to build htty: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Check for ht binary
    ht_binary = output_path / "bin" / "ht"
    assert ht_binary.exists(), f"Missing ht binary at: {ht_binary}"
    assert ht_binary.is_file(), f"ht should be a file, not directory: {ht_binary}"


@pytest.mark.htty
def test_htty_htty_binary():
    """Test that htty package contains htty binary"""
    result = subprocess.run(
        ["nix", "build", ".#htty", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to build htty: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Check for htty binary
    htty_binary = output_path / "bin" / "htty"
    assert htty_binary.exists(), f"Missing htty binary at: {htty_binary}"
    assert htty_binary.is_file(), f"htty should be a file, not directory: {htty_binary}"


@pytest.mark.htty
def test_htty_environment_variables():
    """Test that HTTY_PATH environment variable is set correctly in pytest-htty shell"""
    # This test runs in the pytest-htty environment, so HTTY_PATH should be available
    htty_path = os.environ.get("HTTY_PATH")
    assert htty_path, "HTTY_PATH environment variable not set"

    # Verify the path points to a valid htty installation
    htty_path = Path(htty_path)
    assert htty_path.exists(), f"HTTY_PATH points to non-existent directory: {htty_path}"
    assert (htty_path / "bin" / "ht").exists(), "ht binary not found in HTTY_PATH"
    assert (htty_path / "bin" / "htty").exists(), "htty binary not found in HTTY_PATH"


@pytest.mark.sdist
def test_htty_sdist_environment_variables():
    """Test that HTTY_SDIST_PATH environment variable is set correctly in pytest-sdist shell"""
    # This test runs in the pytest-sdist environment, so HTTY_SDIST_PATH should be available
    sdist_path = os.environ.get("HTTY_SDIST_PATH")
    assert sdist_path, "HTTY_SDIST_PATH environment variable not set"

    # Verify the path points to a valid sdist output
    sdist_path = Path(sdist_path)
    assert sdist_path.exists(), f"HTTY_SDIST_PATH points to non-existent directory: {sdist_path}"

    # Check for at least one .tar.gz file
    tgz_files = list(sdist_path.glob("*.tar.gz"))
    assert len(tgz_files) >= 1, f"No .tar.gz files found in HTTY_SDIST_PATH: {sdist_path}"
