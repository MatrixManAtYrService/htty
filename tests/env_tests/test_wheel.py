"""Test htty-core-wheel package for expected wheel outputs"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.wheel
def test_htty_core_wheel_file_output(project_root: Path):
    """Test that htty-core-wheel produces a .whl file"""
    result = subprocess.run(
        ["nix", "build", ".#htty-core-wheel", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    assert result.returncode == 0, f"Failed to build htty-core-wheel: {result.stderr}"

    output_path = result.stdout.strip()
    assert output_path, "No output path returned"

    # Check that the output contains a .whl file
    whl_files = list(Path(output_path).glob("*.whl"))
    assert len(whl_files) == 1, f"Expected exactly one .whl file, found: {whl_files}"

    # Check that it's named correctly
    whl_file = whl_files[0]
    assert "htty_core" in whl_file.name, f"Expected htty_core in filename, got: {whl_file.name}"
    assert whl_file.name.endswith(".whl"), f"Expected .whl extension, got: {whl_file.name}"


@pytest.mark.wheel
def test_htty_core_wheel_metadata_files(project_root: Path):
    """Test that htty-core-wheel produces metadata files"""
    result = subprocess.run(
        ["nix", "build", ".#htty-core-wheel", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    assert result.returncode == 0, f"Failed to build htty-core-wheel: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Check for metadata files
    assert (output_path / "wheel-filename.txt").exists(), "Missing wheel-filename.txt"
    assert (output_path / "wheel-path.txt").exists(), "Missing wheel-path.txt"


@pytest.mark.wheel
def test_htty_core_wheel_filename_content(project_root: Path):
    """Test that wheel-filename.txt contains the correct wheel filename"""
    result = subprocess.run(
        ["nix", "build", ".#htty-core-wheel", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    assert result.returncode == 0, f"Failed to build htty-core-wheel: {result.stderr}"

    output_path = Path(result.stdout.strip())

    # Read the wheel filename from metadata
    wheel_filename_file = output_path / "wheel-filename.txt"
    assert wheel_filename_file.exists(), "wheel-filename.txt not found"

    wheel_filename = wheel_filename_file.read_text().strip()

    # Verify the filename matches expected pattern
    assert "htty_core-" in wheel_filename, f"Expected htty_core- in filename, got: {wheel_filename}"
    assert wheel_filename.endswith(".whl"), f"Expected .whl extension, got: {wheel_filename}"

    # Verify the actual wheel file exists with this name
    actual_wheel_file = output_path / wheel_filename
    assert actual_wheel_file.exists(), f"Wheel file not found: {actual_wheel_file}"


@pytest.mark.wheel
def test_htty_core_wheel_environment_variables():
    """Test that HTTY_CORE_WHEEL_PATH environment variable is set correctly in pytest-wheel shell"""
    # This test runs in the pytest-wheel environment, so HTTY_CORE_WHEEL_PATH should be available
    wheel_path = os.environ.get("HTTY_CORE_WHEEL_PATH")
    assert wheel_path, "HTTY_CORE_WHEEL_PATH environment variable not set"

    # Verify the path points to a valid wheel output
    wheel_path = Path(wheel_path)
    assert wheel_path.exists(), f"HTTY_CORE_WHEEL_PATH points to non-existent directory: {wheel_path}"

    # Check for at least one .whl file
    whl_files = list(wheel_path.glob("*.whl"))
    assert len(whl_files) >= 1, f"No .whl files found in HTTY_CORE_WHEEL_PATH: {wheel_path}"

    # Check for metadata files
    assert (wheel_path / "wheel-filename.txt").exists(), "wheel-filename.txt not found in HTTY_CORE_WHEEL_PATH"
    assert (wheel_path / "wheel-path.txt").exists(), "wheel-path.txt not found in HTTY_CORE_WHEEL_PATH"
