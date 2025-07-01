"""Test htty module import availability across different environments"""

import subprocess

import pytest


@pytest.mark.full
@pytest.mark.sdist
def test_has_htty():
    """Test that htty module can be imported"""
    result = subprocess.run(
        ["python", "-c", "import htty; print('htty import success')"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Failed to import htty: {result.stderr}"
    assert "htty import success" in result.stdout


@pytest.mark.empty
@pytest.mark.cli
def test_has_no_htty():
    """Test that htty module cannot be imported"""
    import tempfile

    # Run from a temporary directory to avoid picking up source code from current directory
    with tempfile.TemporaryDirectory() as temp_dir:
        result = subprocess.run(
            ["python", "-c", "import htty"],
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )

        # Should fail with ModuleNotFoundError
        assert result.returncode != 0, "htty import should fail in this environment"
        assert "ModuleNotFoundError" in result.stderr, (
            f"Expected ModuleNotFoundError, got: {result.stderr}"
        )
        assert "No module named 'htty'" in result.stderr, (
            f"Expected specific error message, got: {result.stderr}"
        )
