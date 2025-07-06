"""Test nix packages directly using nix shell commands"""

import subprocess

import pytest


@pytest.mark.htty
def test_nix_htty_import():
    """Test that htty package allows Python import"""
    result = subprocess.run(
        ["nix", "shell", ".#htty", "--command", "python", "-c", "import htty"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to import htty from htty package: {result.stderr}"


@pytest.mark.core
def test_nix_htty_core_import():
    """Test that htty-core-env package allows Python import"""
    result = subprocess.run(
        [
            "nix",
            "shell",
            ".#htty-core-env",
            "--command",
            "python",
            "-c",
            "import htty_core",
        ],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"Failed to import htty_core from htty-core-env: {result.stderr}"


@pytest.mark.htty
def test_nix_htty_ht_command():
    """Test that htty package provides ht command"""
    result = subprocess.run(
        ["nix", "shell", ".#htty", "--command", "ht", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"ht command failed from htty: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_no_ht_command():
    """Test that htty-cli package does not provide ht command in PATH"""
    result = subprocess.run(
        ["nix", "shell", ".#htty-cli", "--command", "bash", "-c", "which ht"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    # Should fail - ht should not be in PATH
    assert result.returncode != 0, "ht command should not be in PATH for htty-cli package"


@pytest.mark.htty
def test_nix_htty_htty_command():
    """Test that htty package provides htty command"""
    result = subprocess.run(
        ["nix", "shell", ".#htty", "--command", "htty", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"htty command failed from htty package: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_htty_command():
    """Test that htty-cli package provides htty command"""
    result = subprocess.run(
        ["nix", "shell", ".#htty-cli", "--command", "htty", "--help"],
        capture_output=True,
        text=True,
        cwd="/Users/matt/src/ht",
    )

    assert result.returncode == 0, f"htty command failed from htty-cli: {result.stderr}"


@pytest.mark.cli
def test_nix_htty_cli_no_python_import():
    """Test that htty-cli package does not provide Python module access"""
    import tempfile
    from pathlib import Path

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent

    # Run from a temporary directory to avoid picking up source code from current directory
    with tempfile.TemporaryDirectory() as temp_dir:
        result = subprocess.run(
            [
                "nix",
                "shell",
                f"{project_root}#htty-cli",
                "--command",
                "python",
                "-c",
                "import htty",
            ],
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )

        # Should fail - htty-cli avoids providing Python module access
        assert result.returncode != 0, "htty import should fail from htty-cli package"
        assert "ModuleNotFoundError" in result.stderr, f"Expected ModuleNotFoundError, got: {result.stderr}"


# Note: htty-py-sdist package has been removed in favor of the htty-core/htty split
# The pytest-sdist environment now uses the complete htty package
