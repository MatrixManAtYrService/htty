"""
Simple test using the htty module to make assertions about terminal output.
Adapted from the original htty test suite.
"""

import logging
import sys
import time
from collections.abc import Generator
from pathlib import Path
from textwrap import dedent
from time import sleep

import pytest

from htty import HtWrapper, Press, SnapshotResult, run, terminal_session


@pytest.fixture
def test_logger() -> logging.Logger:
    """Create a custom logger for tests that doesn't propagate to pytest's loggers."""
    logger = logging.getLogger("htty.test")
    logger.setLevel(logging.DEBUG)

    # Don't propagate to avoid pytest's dual logging system
    logger.propagate = False

    # Add a simple console handler for live logging
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        # Simple format: just "ht stderr:" instead of timestamps and logger names
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


@pytest.fixture
def hello_world_script() -> Generator[str, None, None]:
    # Use a fixed filename in /tmp so it can be run manually after tests
    script_path = "/tmp/htty_test_hello_world.py"

    with open(script_path, "w") as f:
        f.write(
            dedent("""
            print("hello")
            input()
            print("world")
            input()
            print("goodbye")
        """)
        )

    yield script_path
    # Don't delete the file so it can be run manually after tests
    # try:
    #     os.unlink(script_path)
    # except OSError:
    #     pass


@pytest.mark.htty
def test_hello_world_with_scrolling(hello_world_script: str, test_logger: logging.Logger) -> None:
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=3, cols=8, logger=test_logger)
    assert proc.snapshot().text == ("hello   \n        \n        ")
    # hello has scrolled out of view
    proc.send_keys(Press.ENTER)
    assert proc.snapshot().text == ("        \nworld   \n        ")
    proc.send_keys(Press.ENTER)
    proc.ht.exit()  # Clean up the ht process


@pytest.mark.htty
def test_hello_world_after_exit(hello_world_script: str, test_logger: logging.Logger) -> None:
    cmd = f"{sys.executable} {hello_world_script}"
    helloworld = run(cmd, rows=6, cols=8, logger=test_logger)
    helloworld.send_keys(Press.ENTER)
    helloworld.send_keys(Press.ENTER)
    helloworld.cmd.wait()
    assert helloworld.snapshot().text == ("hello   \n        \nworld   \n        \ngoodbye \n        ")

    exit_code = helloworld.ht.exit()
    assert helloworld.cmd.exit_code == 0
    assert exit_code == 0


@pytest.mark.htty
def test_outputs(hello_world_script: str, test_logger: logging.Logger) -> None:
    cmd = f"{sys.executable} {hello_world_script}"
    helloworld = run(cmd, rows=4, cols=8, logger=test_logger)
    helloworld.send_keys(Press.ENTER)  # First input() call
    helloworld.send_keys(Press.ENTER)  # Second input() call to let script finish
    # Wait for the script to complete naturally
    helloworld.cmd.wait()

    # Be more tolerant of how output gets split across events
    # Just check that we got the expected content across all output events
    all_output_text = "".join(str(event.get("data", {}).get("seq", "")) for event in helloworld.get_output())

    # Should contain all the expected text (now that we let it complete)
    assert "hello" in all_output_text, f"Expected 'hello' in output: {all_output_text}"
    assert "world" in all_output_text, f"Expected 'world' in output: {all_output_text}"
    assert "goodbye" in all_output_text, f"Expected 'goodbye' in output: {all_output_text}"

    # Should have at least some output events
    assert len(helloworld.get_output()) > 0, "Should have at least one output event"

    helloworld.ht.exit()  # Clean up the ht process


@pytest.mark.htty
def test_enum_keys_interface(hello_world_script: str) -> None:
    """Test that the new enum keys interface works correctly."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=3, cols=8)
    proc.send_keys(Press.ENTER)

    assert proc.snapshot().text == ("        \nworld   \n        ")
    proc.ht.exit()  # Clean up the ht process


@pytest.mark.htty
def test_html_snapshot_with_colors(colored_hello_world_script: str) -> None:
    """Test that the new SnapshotResult provides HTML with color information."""
    cmd = f"{sys.executable} {colored_hello_world_script}"
    proc = run(cmd, rows=4, cols=8)

    snapshot = proc.snapshot()

    # Test that HTML contains the expected CSS and span for red text
    assert ".ansi31 { color: #aa0000; }" in snapshot.html
    assert '<span class="ansi31">hello</span>' in snapshot.html

    # Continue script to get green "world"
    proc.send_keys(Press.ENTER)

    snapshot2 = proc.snapshot()

    # Test that we now have green color styling too
    assert ".ansi32 { color: #00aa00; }" in snapshot2.html
    assert '<span class="ansi32">world</span>' in snapshot2.html

    # Clean up
    proc.cmd.terminate()
    proc.cmd.wait(timeout=1.0)
    proc.ht.terminate()
    proc.ht.wait(timeout=2.0)


@pytest.mark.htty
def test_context_manager(hello_world_script: str) -> None:
    """Test the context manager API for automatic cleanup."""
    cmd = f"{sys.executable} {hello_world_script}"

    # Test that context manager works and cleans up automatically
    with terminal_session(cmd, rows=3, cols=8) as proc:
        proc.send_keys(Press.ENTER)

        snapshot = proc.snapshot()
        assert "world" in snapshot.text


@pytest.mark.htty
def test_exit_while_subprocess_running(hello_world_script: str) -> None:
    """Test that exit() works reliably even when subprocess is still running."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=4, cols=8, no_exit=True)

    # Take initial snapshot
    snapshot = proc.snapshot()
    assert "hello" in snapshot.text

    # Exit while subprocess is still waiting for input (should force termination)
    exit_code = proc.ht.exit(timeout=5.0)

    # Should exit with forced termination code
    # Unix convention: process terminated by signal N returns exit code -N
    # SIGTERM = signal 15, so terminated by SIGTERM = exit code -15
    assert exit_code == -15

    # Process should be terminated
    assert proc.ht.poll() is not None, "ht process should have exited"


@pytest.mark.htty
def test_exit_after_subprocess_finished(hello_world_script: str) -> None:
    """Test that exit() works when subprocess has already finished."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=4, cols=8, no_exit=True)

    # Complete the script
    proc.send_keys(Press.ENTER)  # First input()
    proc.send_keys(Press.ENTER)  # Second input()

    # Wait for subprocess to finish
    proc.cmd.wait(timeout=3.0)

    # Take final snapshot
    snapshot = proc.snapshot()
    assert "goodbye" in snapshot.text

    # Exit should work cleanly
    exit_code = proc.ht.exit(timeout=5.0)
    assert exit_code == 0

    # Process should be terminated
    assert proc.ht.poll() is not None, "ht process should have exited"


# CLI Example Tests - These translate CLI examples to Python API usage


@pytest.mark.htty
def test_vim_startup_screen(vim_path: Path) -> None:
    """Test equivalent to: htty --snapshot -- vim | grep "VIM - Vi IMproved" """

    proc: HtWrapper = run(str(vim_path), rows=20, cols=50)

    # Wait for Vim to draw its startup screen
    time.sleep(0.1)  # Small delay to allow screen drawing

    # Take snapshot of vim's startup screen
    snapshot: SnapshotResult = proc.snapshot()

    # Look for the line containing "IMproved" (like grep would)
    improved_line = next(line for line in snapshot.text.split("\n") if "IMproved" in line)
    assert improved_line == "~               VIM - Vi IMproved                 "

    # Exit vim
    proc.send_keys(":q!")
    proc.send_keys(Press.ENTER)
    proc.ht.exit()


@pytest.mark.htty
def test_vim_startup_screen_context_manager(vim_path: Path) -> None:
    """Test equivalent to: htty --snapshot -- vim | grep "VIM - Vi IMproved" (using context manager)"""

    with terminal_session(str(vim_path), rows=20, cols=50) as vim:
        # Small delay to allow vim to draw its startup screen
        # Without this, we might snapshot before the screen is ready
        sleep(0.1)
        startup = vim.snapshot()

    improved_line = next(line for line in startup.text.split("\n") if "IMproved" in line)
    assert improved_line == "~               VIM - Vi IMproved                 "


@pytest.mark.htty
def test_vim_duplicate_line(vim_path: Path) -> None:
    """Test equivalent to: htty --rows 5 --cols 20 -k 'ihello,Escape' --snapshot
    -k 'Vyp,Escape' --snapshot -k ':q!,Enter' -- vim"""

    proc = run(str(vim_path), rows=5, cols=20)

    # Send keys: "ihello,Escape" (enter insert mode, type hello, exit insert mode)
    proc.send_keys("i")
    proc.send_keys("hello")
    proc.send_keys(Press.ESCAPE)

    # First snapshot - should show "hello"
    snapshot1 = proc.snapshot()
    assert "hello" in snapshot1.text

    # Send keys: "Vyp,Escape" (visual line mode, yank, put, escape)
    proc.send_keys("V")  # Visual line mode
    proc.send_keys("y")  # Yank (copy) the line
    proc.send_keys("p")  # Put (paste) the line
    proc.send_keys(Press.ESCAPE)  # Exit visual mode

    # Second snapshot - should show "hello" duplicated
    snapshot2 = proc.snapshot()
    text_lines = [line.strip() for line in snapshot2.text.split("\n") if line.strip()]
    hello_lines = [line for line in text_lines if "hello" in line]
    assert len(hello_lines) >= 2, f"Expected duplicated 'hello' lines, got: {text_lines}"

    # Send keys: ":q!,Enter" (quit without saving)
    proc.send_keys(":q!")
    proc.send_keys(Press.ENTER)
    proc.ht.exit()


@pytest.mark.htty
def test_readme_example(vim_path: Path, test_logger: logging.Logger) -> None:
    with terminal_session(str(vim_path), rows=20, cols=50, logger=test_logger) as vim:
        vim.expect("version 9.1.1336")  # wait for vim to finish drawing its startup screen
        startup = vim.snapshot()

        vim.send_keys("i")
        vim.send_keys("hello world")
        vim.send_keys(Press.ESCAPE)
        vim.expect_absent("INSERT")  # wait for vim to return to normal mode
        hello = vim.snapshot()

    improved_line = next(line for line in startup.text.splitlines() if "IMproved" in line)
    assert improved_line == "~               VIM - Vi IMproved                 "

    assert hello.text.split("\n")[0].strip() == "hello world"


@pytest.mark.htty
def test_docs_example(test_logger: logging.Logger) -> None:
    sh = r'PS1="$ " sh -i'  # prompt: $ █
    # not: sh-5.2$ █

    command = r"printf '\n\n\n\nhello world\n'"
    with terminal_session(sh, rows=4, cols=6, logger=test_logger) as bash:
        bash.send_keys([command, Press.ENTER])
        bash.expect("world")
        hello = bash.snapshot()

        bash.send_keys(["clear", Press.ENTER])
        bash.expect_absent("world")
        bash.expect("\\$")
        cleared = bash.snapshot()

    assert hello.text == "\n".join(
        [
            "      ",  # line wrap after 6 chars
            "hello ",
            "world ",
            "$     ",  # four columns wide
        ]
    )

    assert cleared.text == "\n".join(
        [
            "$     ",  # cleared
            "      ",
            "      ",
            "      ",
        ]
    )


@pytest.mark.htty
def test_expect_regex(colored_hello_world_script: str, test_logger: logging.Logger) -> None:
    """Test that expect and expect_absent support regex patterns."""
    cmd = f"{sys.executable} {colored_hello_world_script}"
    with terminal_session(cmd, rows=4, cols=8, logger=test_logger) as proc:
        proc.expect("^hello\\s*$")  # hello with optional trailing whitespace
        proc.expect_absent("world")  # no "world" yet
        proc.send_keys(Press.ENTER)
        proc.expect("world")  # world appears
        proc.send_keys(Press.ENTER)
        proc.expect("goodbye")  # goodbye


@pytest.mark.htty
def test_expect_timeout(colored_hello_world_script: str, test_logger: logging.Logger) -> None:
    """Test that expect times out if pattern is not found."""
    cmd = f"{sys.executable} {colored_hello_world_script}"
    with (
        pytest.raises(
            TimeoutError,
            match=r"Pattern 'nonexistent' not found within \d+\.\d+ seconds",
        ),
        terminal_session(cmd, rows=4, cols=8, logger=test_logger) as proc,
    ):
        proc.expect("nonexistent", timeout=1.0)  # Pattern that will never appear


@pytest.mark.htty
def test_expect_absent_timeout(colored_hello_world_script: str, test_logger: logging.Logger) -> None:
    """Test that expect_absent times out if pattern doesn't disappear."""
    cmd = f"{sys.executable} {colored_hello_world_script}"
    with (
        pytest.raises(TimeoutError, match=r"Pattern 'hello' still present after \d+\.\d+ seconds"),
        terminal_session(cmd, rows=4, cols=8, logger=test_logger) as proc,
    ):
        proc.expect("hello")  # Wait for hello to appear
        proc.expect_absent("hello", timeout=1.0)  # It won't disappear until we press Enter
