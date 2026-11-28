"""Import errors shared by the Telegram parsers and the job runner.

The package is named ``imports`` (not ``import``): ``import`` is a Python
keyword and cannot appear in a normal ``from ... import ...`` statement.
"""
from __future__ import annotations


class ImportParseError(ValueError):
    """Input is not a supported chat export (→ ``IMPORT_PARSE_FAILED``)."""


class ImportTooLarge(ValueError):
    """Input exceeds a hard limit (→ ``IMPORT_TOO_LARGE`` / 413)."""
