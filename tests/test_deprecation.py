### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library

## Installed
import pytest

## Application
import pythonjsonlogger


### TESTS
### ============================================================================
def test_jsonlogger_deprecated():
    with pytest.deprecated_call():
        pythonjsonlogger.jsonlogger
    return


def test_jsonlogger_reserved_attrs_deprecated():
    with pytest.deprecated_call():
        # Note: We use json instead of jsonlogger as jsonlogger will also produce
        # a DeprecationWarning and we specifically want the one for RESERVED_ATTRS
        pythonjsonlogger.json.RESERVED_ATTRS
    return
