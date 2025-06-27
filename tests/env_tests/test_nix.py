"""Test nix packages directly using nix shell commands"""

import subprocess
import pytest


@pytest.mark.sdist
def test_nix_htty_py_sdist_import():
    """Test that htty-py-sdist package allows Python import"""
    result = subprocess.run([
        "nix", "shell", ".#htty-py-sdist", "--command",
        "python", "-c", "import htty"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"Failed to import htty from htty-py-sdist: {result.stderr}"


@pytest.mark.wheel
def test_nix_htty_pylib_import():
    """Test that htty-pylib package allows Python import"""
    result = subprocess.run([
        "nix", "shell", ".#htty-pylib", "--command",
        "python", "-c", "import htty"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"Failed to import htty from htty-pylib: {result.stderr}"


@pytest.mark.wheel
def test_nix_htty_pylib_ht_command():
    """Test that htty-pylib package provides ht command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-pylib", "--command",
        "ht", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"ht command failed from htty-pylib: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_ht_command():
    """Test that htty-cli package provides ht command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-cli", "--command",
        "ht", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"ht command failed from htty-cli: {result.stderr}"


@pytest.mark.wheel
def test_nix_htty_pylib_htty_command():
    """Test that htty-pylib package provides htty command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-pylib", "--command",
        "htty", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"htty command failed from htty-pylib: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_htty_command():
    """Test that htty-cli package provides htty command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-cli", "--command",
        "htty", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    assert result.returncode == 0, f"htty command failed from htty-cli: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_no_python_import():
    """Test that htty-cli package does not provide Python module"""
    result = subprocess.run([
        "nix", "shell", ".#htty-cli", "--command",
        "python", "-c", "import htty"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    # Should fail with ModuleNotFoundError
    assert result.returncode != 0, "htty import should fail from htty-cli package"
    assert "ModuleNotFoundError" in result.stderr, f"Expected ModuleNotFoundError, got: {result.stderr}"


@pytest.mark.sdist
def test_nix_htty_py_sdist_no_ht_command():
    """Test that htty-py-sdist package does not provide ht command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-py-sdist", "--command",
        "ht", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    # Should fail with command not found
    assert result.returncode != 0, "ht command should fail from htty-py-sdist package"


@pytest.mark.sdist
def test_nix_htty_py_sdist_no_htty_command():
    """Test that htty-py-sdist package does not provide htty command"""
    result = subprocess.run([
        "nix", "shell", ".#htty-py-sdist", "--command",
        "htty", "--help"
    ], capture_output=True, text=True, cwd="/Users/matt/src/ht")
    
    # Should fail with command not found
    assert result.returncode != 0, "htty command should fail from htty-py-sdist package"
    assert "No such file or directory" in result.stderr or "not found" in result.stderr, f"Expected command not found error, got: {result.stderr}"



