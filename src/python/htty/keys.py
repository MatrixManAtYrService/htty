"""
Key definitions for htty
Based on the key parsing logic in ht's stdio.rs file.
"""

from enum import Enum
from typing import List, Union

# exclude this module from docs
__all__ = ["Press", "KeyInput", "key_to_string", "keys_to_strings"]


class Press(Enum):
    """Key constants for terminal input - comprehensive set"""
    ENTER = "Enter"
    TAB = "Tab"
    SPACE = "Space"
    ESCAPE = "Escape"
    LEFT = "Left"
    RIGHT = "Right"
    UP = "Up"
    DOWN = "Down"
    HOME = "Home"
    END = "End"
    PAGE_UP = "PageUp"
    PAGE_DOWN = "PageDown"
    BACKSPACE = "Backspace"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"
    CTRL_A = "C-a"
    CTRL_B = "C-b"
    CTRL_C = "C-c"
    CTRL_D = "C-d"
    CTRL_E = "C-e"
    CTRL_F = "C-f"
    CTRL_G = "C-g"
    CTRL_H = "C-h"
    CTRL_I = "C-i"
    CTRL_J = "C-j"
    CTRL_K = "C-k"
    CTRL_L = "C-l"
    CTRL_M = "C-m"
    CTRL_N = "C-n"
    CTRL_O = "C-o"
    CTRL_P = "C-p"
    CTRL_Q = "C-q"
    CTRL_R = "C-r"
    CTRL_S = "C-s"
    CTRL_T = "C-t"
    CTRL_U = "C-u"
    CTRL_V = "C-v"
    CTRL_W = "C-w"
    CTRL_X = "C-x"
    CTRL_Y = "C-y"
    CTRL_Z = "C-z"


# Type alias for key input (single key or string)
KeyInput = Union[str, Press]


def key_to_string(key: KeyInput) -> str:
    """Convert a key input to its string representation."""
    if isinstance(key, Press):
        return key.value
    return str(key)


def keys_to_strings(keys: Union[KeyInput, List[KeyInput]]) -> List[str]:
    """Convert key inputs to a list of string representations."""
    if isinstance(keys, (str, Press)):
        return [key_to_string(keys)]
    return [key_to_string(key) for key in keys]
