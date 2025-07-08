"""Tests for the htty command line interface via subprocess."""

import contextlib
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Union

import pytest

src_path = Path(__file__).parent.parent / "src"

env = {**os.environ, "HTTY_HT_BIN": os.environ.get("HTTY_HT_BIN", "")}

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    lines: list[Union[str, re.Pattern[str]]]


def terminal_contents(*, actual_snapshots: str, expected_patterns: list[Pattern]) -> bool:
    """Check if the actual snapshot matches the expected patterns in order."""
    # Split into lines without stripping leading/trailing newlines to preserve empty lines
    actual_lines = actual_snapshots.split("\n")

    # Remove trailing empty lines to avoid issues with terminal padding,
    # but preserve leading empty lines and strip trailing whitespace from non-empty lines
    while actual_lines and actual_lines[-1].strip() == "":
        actual_lines.pop()

    # Strip trailing whitespace from each line but preserve empty lines
    actual_lines = [line.rstrip() for line in actual_lines]

    pattern_idx = 0
    for pattern_idx, pattern in enumerate(expected_patterns):
        # Check if there are enough lines left for this pattern
        if len(actual_lines) < len(pattern.lines):
            print(
                f"Pattern {pattern_idx}: Not enough actual lines. "
                f"Expected {len(pattern.lines)}, got {len(actual_lines)}"
            )
            return False

        # Match each line in the pattern
        for line_idx, expected_line in enumerate(pattern.lines):
            if line_idx >= len(actual_lines):
                print(f"Pattern {pattern_idx}, line {line_idx}: Actual snapshot too short")
                return False

            actual_line = actual_lines[line_idx]

            if isinstance(expected_line, re.Pattern):
                # This is a compiled regex pattern
                if not expected_line.match(actual_line):
                    print(
                        f"Pattern {pattern_idx}, line {line_idx}: Regex {expected_line.pattern} "
                        f"failed to match '{actual_line}'"
                    )
                    return False
            else:
                # This is a string that should be matched exactly
                if expected_line != actual_line:
                    print(f"Pattern {pattern_idx}, line {line_idx}: Expected '{expected_line}', got '{actual_line}'")
                    return False

        # Remove the matched lines from actual_lines for the next pattern
        actual_lines = actual_lines[len(pattern.lines) :]

    return True


@pytest.mark.cli
def test_echo_hello() -> None:
    cmd = [
        "htty",
        *("-r", "2"),
        *("-c", "10"),
        "--",
        *("echo", "hello"),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello\n\n"
    actual_output = ran.stdout.replace("----\n", "")
    assert actual_output == expected_output


@pytest.mark.htty
def test_keys_after_subproc_exit() -> None:
    cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-r", "2"),
        *("-c", "10"),
        # echo hello will happen immediately and the subprocess will close
        # then we'll attempt to send text anyway
        *("-k", "world"),
        "--",
        *("echo", "hello"),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello\n\n----\n"
    assert ran.stdout == expected_output
    print(ran.stderr)


@pytest.fixture
def greeter_script() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            dedent(
                """
                name = input()
                print("hello", name)
                """
            ).encode("utf-8")
        )
        tmp_path = tmp.name

    yield tmp_path
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)


@pytest.mark.htty
def test_send_keys(greeter_script: str) -> None:
    cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-r", "2"),
        *("-c", "10"),
        *("-k", "world,Backspace,Enter"),
        "--",
        *(sys.executable, greeter_script),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello worl\n\n"
    actual_output = ran.stdout.replace("----\n", "")
    assert actual_output == expected_output


@pytest.mark.htty
def test_vim(vim_path: Path) -> None:
    cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        "--snapshot",
        *("-k", "ihello,Escape"),
        "--snapshot",
        *("-k", ":q!,Enter"),
        "--",
        str(vim_path),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

    snapshots = ran.stdout.split("----\n")
    snapshots = [s for s in snapshots if s.strip()]
    assert len(snapshots) == 2, f"Expected 2 snapshots, got {len(snapshots)}"

    # Test first snapshot (vim opening screen)
    assert terminal_contents(
        actual_snapshots=snapshots[0],
        expected_patterns=[
            Pattern(
                lines=[
                    "",
                    "~",
                    "~",
                    "~",
                    "~               VIM - Vi IMproved",
                    "~",
                    "~                version 9.1.1336",
                    "~            by Bram Moolenaar et al.",
                    "~  Vim is open source and freely distributable",
                    "~",
                    re.compile(r"~.*"),  # Variable message line 1
                    re.compile(r"~ type  :help .*"),  # Variable help command
                    "~",
                    "~ type  :q<Enter>               to exit",
                    "~ type  :help<Enter>  or  <F1>  for on-line help",
                    "~ type  :help version9<Enter>   for version info",
                    "~",
                    "~",
                    "~",
                    "                                0,0-1         All",
                ],
            ),
        ],
    )

    # Test second snapshot (after typing hello and pressing Escape)
    assert terminal_contents(
        actual_snapshots=snapshots[1],
        expected_patterns=[
            Pattern(
                lines=[
                    "hello",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "                                1,5           All",
                ],
            ),
        ],
    )

    # Clean up vim
    cleanup_cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-k", ":q!,Enter"),
        "--",
        str(vim_path),
    ]
    subprocess.run(cleanup_cmd, check=True, env=env)


@pytest.mark.htty
def test_empty_line_preservation():
    """Test that CLI preserves empty lines at the beginning of output."""
    import os
    import tempfile

    # Create a script that outputs an empty line followed by "hello"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("print()  # Empty line\n")
        f.write('print("hello")\n')
        script_path = f.name

    try:
        cmd = [
            *(sys.executable, "-m"),
            "htty.cli",
            "--snapshot",
            "--",
            sys.executable,
            script_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

        # Parse the snapshot using the same logic as other tests
        snapshots = result.stdout.split("----\n")
        snapshots = [s for s in snapshots if s.strip()]
        assert len(snapshots) == 1, f"Expected 1 snapshot, got {len(snapshots)}"

        # Verify using terminal_contents function
        assert terminal_contents(
            actual_snapshots=snapshots[0],
            expected_patterns=[
                Pattern(
                    lines=[
                        "",  # Empty first line
                        "hello",  # Second line with content
                    ]
                ),
            ],
        )

    finally:
        os.unlink(script_path)


@pytest.mark.htty
def test_readme_example_cli(vim_path: Path) -> None:
    """Test the readme example using CLI arguments instead of Python API."""
    cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-r", "20"),  # rows
        *("-c", "50"),  # cols
        *("--expect", "version 9.1.1336"),  # wait for vim to finish drawing startup screen
        "--snapshot",  # capture startup screen
        *("-k", "i"),  # enter insert mode
        *("-k", "hello world"),  # type text
        *("-k", "Escape"),  # exit insert mode
        *("--expect-absent", "INSERT"),  # wait for INSERT mode indicator to disappear
        "--snapshot",  # capture final screen
        "--",
        str(vim_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

    # Parse the snapshots
    snapshots = result.stdout.split("----\n")
    snapshots = [s for s in snapshots if s.strip()]
    assert len(snapshots) == 2, f"Expected 2 snapshots, got {len(snapshots)}"

    # Test startup screen snapshot
    assert terminal_contents(
        actual_snapshots=snapshots[0],
        expected_patterns=[
            Pattern(
                lines=[
                    "",
                    "~",
                    "~",
                    "~",
                    "~               VIM - Vi IMproved",
                    "~",
                    "~                version 9.1.1336",
                    "~            by Bram Moolenaar et al.",
                    "~  Vim is open source and freely distributable",
                    "~",
                    re.compile(r"~.*"),  # Variable message line 1
                    re.compile(r"~ type  :help .*"),  # Variable help command
                    "~",
                    "~ type  :q<Enter>               to exit",
                    "~ type  :help<Enter>  or  <F1>  for on-line help",
                    "~ type  :help version9<Enter>   for version info",
                    "~",
                    "~",
                    "~",
                    "                                0,0-1         All",
                ],
            ),
        ],
    )

    # Test final screen snapshot
    assert terminal_contents(
        actual_snapshots=snapshots[1],
        expected_patterns=[
            Pattern(
                lines=[
                    "hello world",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "                                1,11          All",
                ],
            ),
        ],
    )

    # Clean up vim
    cleanup_cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-k", ":q!,Enter"),
        "--",
        str(vim_path),
    ]
    subprocess.run(cleanup_cmd, check=True, env=env)


@pytest.mark.htty
def test_expect_regex_cli(colored_hello_world_script: str) -> None:
    """Test the regex expect/expect-absent functionality using CLI arguments."""
    cmd = [
        *(sys.executable, "-m"),
        "htty.cli",
        *("-r", "4"),  # rows
        *("-c", "8"),  # cols
        *("--expect", "hello"),  # wait for "hello" to appear (simpler pattern)
        "--snapshot",  # capture hello screen
        *("-k", "Enter"),  # press enter
        *("--expect", "world"),  # wait for "world" to appear
        "--snapshot",  # capture world screen
        *("-k", "Enter"),  # press enter
        *("--expect", "goodbye"),  # wait for "goodbye" to appear
        "--snapshot",  # capture final screen
        "--",
        sys.executable,  # Run with Python
        colored_hello_world_script,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

    # Parse the snapshots
    snapshots = result.stdout.split("----\n")
    snapshots = [s for s in snapshots if s.strip()]
    assert len(snapshots) == 3, f"Expected 3 snapshots, got {len(snapshots)}"

    # Just check that the text contains the expected words -
    # don't worry about exact ANSI sequences which can vary
    assert "hello" in snapshots[0]
    assert "world" in snapshots[1]
    assert "goodbye" in snapshots[2]
