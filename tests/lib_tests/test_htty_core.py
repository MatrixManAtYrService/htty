"""
Tests for htty_core package - core interface functionality.

These tests only require htty_core and run in the pytest-core environment.
"""

import pytest

# Import htty_core for core interface tests (available in both environments)
from htty_core import HtArgs, HtEvent


def test_htargs_creation():
    """Test that HtArgs can be created with proper validation."""
    # Valid args
    args = HtArgs(command=["echo", "hello"], subscribes=[HtEvent.OUTPUT, HtEvent.PID], rows=10, cols=20)
    assert args.command == ["echo", "hello"]
    assert HtEvent.OUTPUT in args.subscribes
    assert HtEvent.PID in args.subscribes
    assert args.rows == 10
    assert args.cols == 20


def test_htargs_validation():
    """Test that HtArgs validates inputs properly."""
    # Empty command should fail
    with pytest.raises(ValueError, match="command cannot be empty"):
        HtArgs(command="", subscribes=[HtEvent.OUTPUT])

    # Empty subscribes should fail
    with pytest.raises(ValueError, match="subscribes cannot be empty"):
        HtArgs(command="echo hello", subscribes=[])

    # Mismatched rows/cols should fail
    with pytest.raises(ValueError, match="both rows and cols must be specified together"):
        HtArgs(command="echo hello", subscribes=[HtEvent.OUTPUT], rows=10)


def test_htevent_enum():
    """Test that HtEvent enum works correctly."""
    assert HtEvent.OUTPUT.value == "output"
    assert HtEvent.PID.value == "pid"
    assert HtEvent.SNAPSHOT.value == "snapshot"
    assert HtEvent.INIT.value == "init"
    assert HtEvent.RESIZE.value == "resize"
    assert HtEvent.EXIT_CODE.value == "exitCode"
    assert HtEvent.COMMAND_COMPLETED.value == "commandCompleted"
    assert HtEvent.DEBUG.value == "debug"

    # Test that we can convert from string
    assert HtEvent("output") == HtEvent.OUTPUT
    assert HtEvent("pid") == HtEvent.PID


def test_htargs_string_command():
    """Test that HtArgs works with string commands too."""
    args = HtArgs(
        command="echo hello world",
        subscribes=[HtEvent.OUTPUT],
    )
    assert args.command == "echo hello world"
    assert args.rows is None
    assert args.cols is None


def test_find_ht_binary():
    """Test that find_ht_binary can locate the bundled binary."""
    from htty_core import find_ht_binary

    # Should not raise an exception in proper environment
    binary_path = find_ht_binary()
    assert binary_path
    assert isinstance(binary_path, str)


def test_run_basic():
    """Test that run() function can create a subprocess."""
    from htty_core import run

    args = HtArgs(command=["echo", "hello"], subscribes=[HtEvent.OUTPUT, HtEvent.PID])

    proc = run(args)
    assert proc is not None
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    # Clean up
    proc.terminate()
    proc.wait()
