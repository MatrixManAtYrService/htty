"""
Unit tests for htty Python code without ht binary.

These tests run in an environment where the ht binary is intentionally not available,
allowing us to test Python logic in isolation with mocked binaries.
"""

import subprocess

import pytest


@pytest.mark.sdist
def test_ht_binary_not_available():
    """Test that ht binary is NOT available in the pure Python environment.

    This ensures we're testing in isolation and can mock the binary behavior.
    """
    with pytest.raises(subprocess.CalledProcessError):
        # This should fail because ht is not available in pure Python env
        result = subprocess.run(["which", "ht"], check=True, capture_output=True, text=True)

    # Also verify using subprocess.run without check=True
    result = subprocess.run(["which", "ht"], capture_output=True, text=True)
    assert result.returncode != 0, "ht binary should not be found in pure Python environment"
    assert result.stdout.strip() == "", "which ht should return empty output"
