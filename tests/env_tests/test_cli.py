"""Test CLI command availability across different environments"""

import subprocess

import pytest


@pytest.mark.htty
def test_has_ht():
    """Test that ht command is available"""
    result = subprocess.run(["ht", "--help"], capture_output=True, text=True)

    assert result.returncode == 0, f"ht command should work: {result.stderr}"


@pytest.mark.empty
def test_has_no_ht():
    """Test that ht command is not available"""
    try:
        result = subprocess.run(["ht", "--help"], capture_output=True, text=True)
        # If command exists but fails, check exit code
        assert result.returncode != 0, "ht command should fail in this environment"
    except FileNotFoundError:
        # Command not found (expected in empty/cli environments)
        pass


@pytest.mark.cli
@pytest.mark.htty
def test_has_htty():
    """Test that htty command is available"""
    try:
        result = subprocess.run(["htty", "--help"], capture_output=True, text=True)

        assert result.returncode == 0, f"htty command should work: {result.stderr}"
    except FileNotFoundError:
        # Command not found - this is the issue that needs to be fixed in wheel environment
        pytest.fail("htty command not found - this indicates the PATH issue that needs to be fixed")


@pytest.mark.empty
def test_has_no_htty():
    """Test that htty command is not available"""
    try:
        result = subprocess.run(["htty", "--help"], capture_output=True, text=True)
        # If command exists but fails, check exit code
        assert result.returncode != 0, "htty command should fail in this environment"
    except FileNotFoundError:
        # Command not found (expected in empty environments)
        pass
