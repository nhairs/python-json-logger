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
