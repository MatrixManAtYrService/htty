"""
Find the ht binary that was installed with this package.
"""
from __future__ import annotations

import os
import sys
import sysconfig


def find_ht_bin() -> str:
    """Return the ht binary path."""

    ht_exe = "ht" + sysconfig.get_config_var("EXE")

    # Check standard script directory first
    path = os.path.join(sysconfig.get_path("scripts"), ht_exe)
    if os.path.isfile(path):
        return path

    # Check user-specific scheme locations
    if sys.version_info >= (3, 10):
        user_scheme = sysconfig.get_preferred_scheme("user")
    elif os.name == "nt":
        user_scheme = "nt_user"
    elif sys.platform == "darwin" and sys._framework:
        user_scheme = "osx_framework_user"
    else:
        user_scheme = "posix_user"

    path = os.path.join(sysconfig.get_path("scripts", scheme=user_scheme), ht_exe)
    if os.path.isfile(path):
        return path

    # Search in `bin` adjacent to package root (as created by `pip install --target`).
    pkg_root = os.path.dirname(os.path.dirname(__file__))
    target_path = os.path.join(pkg_root, "bin", ht_exe)
    if os.path.isfile(target_path):
        return target_path

    raise FileNotFoundError(f"ht binary not found. Searched: {path}")
