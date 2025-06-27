"""Test CLI command availability across different environments"""

import subprocess
import pytest


@pytest.mark.wheel
@pytest.mark.cli
def test_has_ht():
    """Test that ht command is available"""
    result = subprocess.run([
        "ht", "--help"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"ht command should work: {result.stderr}"


@pytest.mark.empty
@pytest.mark.sdist
def test_has_no_ht():
    """Test that ht command is not available"""
    try:
        result = subprocess.run([
            "ht", "--help"
        ], capture_output=True, text=True)
        # If command exists but fails, check exit code
        assert result.returncode != 0, "ht command should fail in this environment"
    except FileNotFoundError:
        # Command not found (expected in empty/sdist environments)
        pass


@pytest.mark.cli
def test_has_htty():
    """Test that htty command is available"""
    result = subprocess.run([
        "htty", "--help"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"htty command should work: {result.stderr}"


@pytest.mark.empty
@pytest.mark.wheel
@pytest.mark.sdist
def test_has_no_htty():
    """Test that htty command is not available"""
    try:
        result = subprocess.run([
            "htty", "--help"
        ], capture_output=True, text=True)
        # If command exists but fails, check exit code
        assert result.returncode != 0, "htty command should fail in this environment"
    except FileNotFoundError:
        # Command not found (expected in empty/wheel/sdist environments)
        pass
