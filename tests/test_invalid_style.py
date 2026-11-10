### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
import re

## Installed
import pytest

## Application
from pythonjsonlogger.json import JsonFormatter


### TESTS
### ============================================================================
def test_invalid_style_error_message_lists_valid_styles():
    """The ValueError for an unknown style must name every valid style.

    Before the fix the message was "Style must be one of: '%{$,'", which
    mashes the four valid styles (``%``, ``{``, ``$`` and ``,``) together
    without separators, so a user cannot tell what to pass.
    """
    expected = "Style must be one of: '%', '{', '$', ','"
    with pytest.raises(ValueError, match=re.escape(expected)):
        JsonFormatter("%(message)s", style="!")
    return
