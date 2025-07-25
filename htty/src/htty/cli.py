#!/usr/bin/env python3
"""
CLI interface for htty providing synchronous batch mode for scripting.
"""

import argparse
import contextlib
import logging
import sys
import time
from typing import Optional, TypeAlias

from htty_core import HtEvent

from .ht import HtWrapper, run
from .keys import KeyInput

# Type alias to avoid triple bracket pattern that confuses Cog
ActionTuple: TypeAlias = tuple[str, Optional[str]]


def parse_keys(keys_str: str, delimiter: str = ",") -> list[KeyInput]:
    """Parse a key sequence string into individual keys."""
    if not keys_str:
        return []

    return [key.strip() for key in keys_str.split(delimiter) if key.strip()]


def htty_sync() -> None:
    """
    Entry point for 'htty' command - synchronous batch mode.

    Processes a sequence of actions and outputs results.
    """
    parser = argparse.ArgumentParser(
        description="Run a command with ht terminal emulation (synchronous mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  htty -- echo hello
  htty -k "hello,Enter" -s -- vim
  htty -r 30 -c 80 -s -k "ihello,Escape" -s -- vim

The -k/--keys, -s/--snapshot, --expect, and --expect-absent options can be used multiple times and will be
processed in order.
        """.strip(),
    )

    parser.add_argument(
        "-r",
        "--rows",
        type=int,
        default=20,
        help="Number of terminal rows (default: 20)",
    )
    parser.add_argument(
        "-c",
        "--cols",
        type=int,
        default=50,
        help="Number of terminal columns (default: 50)",
    )
    parser.add_argument(
        "-k",
        "--keys",
        action="append",
        default=[],
        help="Send keys to the terminal. Can be used multiple times.",
    )
    parser.add_argument(
        "-s",
        "--snapshot",
        action="append_const",
        const=True,
        default=[],
        help="Take a snapshot of terminal output. Can be used multiple times.",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=",",
        help="Delimiter for parsing keys (default: ',')",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode: show ht events and subscribe to debug events",
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="Wait for a regex pattern to appear in the terminal output. Can be used multiple times.",
    )
    parser.add_argument(
        "--expect-absent",
        action="append",
        default=[],
        help="Wait for a regex pattern to disappear from the terminal output. Can be used multiple times.",
    )
    parser.add_argument(
        "--version",
        action="version",
        # [[[cog
        # import os
        # cog.out(f'version="{os.environ["HTTY_VERSION_INFO_HTTY"]}",')
        # ]]]
        version="htty 0.2.27 (unknown)",
        # [[[end]]]
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="Command to run (must be preceded by --)",
    )

    # Find the -- separator to handle command parsing correctly
    try:
        dash_dash_idx = sys.argv.index("--")
        args_before_command = sys.argv[1:dash_dash_idx]
        command = sys.argv[dash_dash_idx + 1 :]
    except ValueError:
        if "--help" in sys.argv or "-h" in sys.argv:
            args_before_command = sys.argv[1:]
            command = []
        else:
            parser.error("No command specified after --")

    args = parser.parse_args(args_before_command)

    if not command:
        if "--help" not in sys.argv and "-h" not in sys.argv:
            parser.error("No command specified after --")
        return

    # Build action sequence from arguments
    actions: list[ActionTuple] = []

    # Simple approach: collect all -k and -s in order they appear
    arg_iter = iter(args_before_command)
    for arg in arg_iter:
        if arg in ["-k", "--keys"]:
            try:
                keys_val = next(arg_iter)
                actions.append(("keys", keys_val))
            except StopIteration:
                parser.error(f"{arg} requires a value")
        elif arg in ["-s", "--snapshot"]:
            actions.append(("snapshot", None))
        elif arg == "--expect":
            try:
                pattern = next(arg_iter)
                actions.append(("expect", pattern))
            except StopIteration:
                parser.error("--expect requires a REGEX pattern")
        elif arg == "--expect-absent":
            try:
                pattern = next(arg_iter)
                actions.append(("expect_absent", pattern))
            except StopIteration:
                parser.error("--expect-absent requires a REGEX pattern")

    try:
        # Set up debug logger if requested
        debug_logger: Optional[logging.Logger] = None
        extra_subscribes: Optional[list[HtEvent]] = None

        if args.debug:
            # Create a debug logger that outputs to stderr
            debug_logger = logging.getLogger("htty.debug")
            debug_logger.setLevel(logging.DEBUG)

            # Add debug handler if not already present
            if not debug_logger.handlers:
                handler = logging.StreamHandler(sys.stderr)
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter("DEBUG: %(message)s")
                handler.setFormatter(formatter)
                debug_logger.addHandler(handler)

            # Subscribe to debug events
            extra_subscribes = [HtEvent.DEBUG]

        # Start the ht process
        proc: HtWrapper = run(
            command,
            rows=args.rows,
            cols=args.cols,
            no_exit=True,
            logger=debug_logger,
            extra_subscribes=extra_subscribes,
        )

        time.sleep(0.1)

        # Process actions in order
        for action_type, action_value in actions:
            if action_type == "keys" and action_value:
                keys = parse_keys(action_value, args.delimiter)
                if keys:
                    # Check if subprocess has completed before sending keys
                    if proc.cmd.completed or proc.cmd.exit_code is not None:
                        if debug_logger:
                            debug_logger.warning(f"Subprocess has completed, skipping keys: {action_value}")
                        continue
                    proc.send_keys(keys)
                    time.sleep(0.05)  # Small delay after sending keys
            elif action_type == "snapshot":
                try:
                    snapshot = proc.snapshot()
                    # Print each line, stripping trailing whitespace
                    for line in snapshot.text.split("\n"):
                        print(line.rstrip())
                    print("----")  # Separator
                except Exception as e:
                    print(f"Error taking snapshot: {e}", file=sys.stderr)
                    print("----")  # Still print separator
            elif action_type == "expect" and action_value:
                try:
                    proc.expect(action_value)
                except Exception as e:
                    print(f"Error waiting for pattern '{action_value}': {e}", file=sys.stderr)
                    sys.exit(1)
            elif action_type == "expect_absent" and action_value:
                try:
                    proc.expect_absent(action_value)
                except Exception as e:
                    print(f"Error waiting for pattern '{action_value}' to disappear: {e}", file=sys.stderr)
                    sys.exit(1)

        # Take a final snapshot if none were explicitly requested
        if not any(action_type == "snapshot" for action_type, _ in actions):
            try:
                snapshot = proc.snapshot()
                for line in snapshot.text.split("\n"):
                    print(line.rstrip())
                print("----")
            except Exception as e:
                print(f"Error taking final snapshot: {e}", file=sys.stderr)
                print("----")

        # Clean exit
        try:
            proc.ht.exit(timeout=5.0)
        except Exception:
            # Force cleanup if needed
            if hasattr(proc, "cmd"):
                with contextlib.suppress(Exception):
                    proc.cmd.terminate()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    htty_sync()
