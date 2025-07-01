"""
HTML utilities for converting ANSI terminal sequences to HTML.
"""

import re

from ansi2html import Ansi2HTMLConverter

__all__ = ["clean_ansi_for_html", "simple_ansi_to_html"]


def clean_ansi_for_html(ansi_text: str) -> str:
    """
    Clean ANSI sequences to keep only color/style codes that ansi2html can handle.

    This function removes:
    - Cursor positioning sequences (\x1b[1;1H, \x1b[2;3H, etc.)
    - Screen buffer switching (\x1b[?1047h, \x1b[?1047l)
    - Scroll region settings (\x1b[1;4r)
    - Save/restore cursor sequences (\x1b7, \x1b8)
    - Other terminal control sequences that don't end with 'm' (color codes)
    - Most control characters except ANSI escape sequences and line breaks
    """
    # Normalize \x9b sequences to \x1b[ sequences for consistency
    ansi_text = ansi_text.replace("\x9b", "\x1b[")

    # Remove cursor positioning sequences like \x1b[1;1H, \x1b[2;3H etc.
    ansi_text = re.sub(r"\x1b\[\d*;\d*H", "", ansi_text)

    # Remove single cursor positioning like \x1b[H
    ansi_text = re.sub(r"\x1b\[H", "", ansi_text)

    # Remove screen buffer switching \x1b[?1047h, \x1b[?1047l
    ansi_text = re.sub(r"\x1b\[\?\d+[hl]", "", ansi_text)

    # Remove scroll region setting \x1b[1;4r
    ansi_text = re.sub(r"\x1b\[\d*;\d*r", "", ansi_text)

    # Remove save/restore cursor sequences \x1b7, \x1b8
    ansi_text = re.sub(r"\x1b[78]", "", ansi_text)

    # Remove other terminal control sequences but keep color codes
    # This removes sequences that don't end with 'm' (which are color codes)
    ansi_text = re.sub(r"\x1b\[(?![0-9;]*m)[^m]*[a-zA-Z]", "", ansi_text)

    # Remove control characters but preserve \x1b which is needed for ANSI codes
    # and preserve \r\n for line breaks
    ansi_text = re.sub(r"[\x00-\x08\x0B-\x1A\x1C-\x1F\x7F-\x9F]", "", ansi_text)

    return ansi_text


def simple_ansi_to_html(ansi_text: str) -> str:
    """
    Convert ANSI terminal sequences to HTML using ansi2html library.
    This matches the original htty behavior.
    """
    # Clean the ANSI text first
    cleaned_seq = clean_ansi_for_html(ansi_text)

    # Use the same converter as original htty
    ansi_converter = Ansi2HTMLConverter()
    html = ansi_converter.convert(cleaned_seq)

    return html
