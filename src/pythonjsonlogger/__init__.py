### IMPORTS
### ============================================================================
## Future

## Standard Library
import sys

## Installed

## Application

### CONSTANTS
### ============================================================================
if sys.implementation.name == "pypy":
    # Per https://github.com/ijl/orjson (last checked 2024-04-28)
    # > orjson does not and will not support PyPy
    ORJSON_AVAILABLE = False
else:
    try:
        import orjson
        ORJSON_AVAILABLE = True
    except ImportError:
        ORJSON_AVAILABLE = False
