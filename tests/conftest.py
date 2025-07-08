import logging
import os
from collections.abc import Generator
from pathlib import Path
from textwrap import dedent

import pytest

# Configure logging for htty tests
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Enable debug logging for htty
logging.getLogger("htty.core").setLevel(logging.DEBUG)


@pytest.fixture
def vim_path() -> Path:
    try:
        vim_path = Path(os.environ["HTTY_TEST_VIM_TARGET"])
        assert vim_path.exists
        return vim_path
    except KeyError as err:
        raise LookupError("HTTY_TEST_VIM_TARGET not set - please run in nix devshell") from err


@pytest.fixture
def colored_hello_world_script() -> Generator[str, None, None]:
    # Use a fixed filename in /tmp so it can be run manually after tests
    script_path = "/tmp/htty_test_colored_hello_world.py"

    with open(script_path, "w") as f:
        f.write(
            dedent("""
            print("\\033[31mhello\\033[0m")
            input()
            print("\\033[32mworld\\033[0m")
            input()
            print("\\033[33mgoodbye\\033[0m")
        """)
        )

    yield script_path
    # Don't delete the file so it can be run manually after tests
