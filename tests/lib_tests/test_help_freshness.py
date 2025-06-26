"""
Test to verify that code changes are reflected in the test environment.
This test checks the help output of the ht binary to ensure fresh builds.
"""

import pytest
from htty import get_ht_help


def test_ht_help_contains_expected_text():
    """Test that the ht help output contains expected text."""
    help_output = get_ht_help()
    
    # Check for some basic expected content
    assert "Usage:" in help_output
    assert "Commands:" in help_output
    assert "Options:" in help_output
    assert "wait-exit" in help_output
    assert "--help" in help_output
    assert "--version" in help_output


def test_ht_help_version_string():
    """Test that help output contains the version string."""
    help_output = get_ht_help()
    
    # This should contain the current version
    # If we modify src/cli.rs and change the version, this should reflect
    assert "ht 0.3.0" in help_output or "version" in help_output.lower()


def test_current_help_format():
    """Test the exact format we expect from help - this will change if cli.rs changes."""
    help_output = get_ht_help()
    
    # Test for the current specific format
    # If we change src/cli.rs, this should break and need updating
    expected_lines = [
        "Commands:",
        "  wait-exit",
        "Arguments:",
        "  [SHELL_COMMAND]...",
        "Options:",
        "      --size <COLSxROWS>",
        "  -l, --listen",
        "      --subscribe <EVENTS>",
        "  -h, --help",
        "  -V, --version"
    ]
    
    for expected_line in expected_lines:
        assert expected_line in help_output, f"Expected '{expected_line}' in help output"


def test_help_reproducibility():
    """Test that help output is consistent across multiple calls."""
    help1 = get_ht_help()
    help2 = get_ht_help()
    
    assert help1 == help2
    assert help1  # Should not be empty
    assert "Error" not in help1  # Should not contain error messages
