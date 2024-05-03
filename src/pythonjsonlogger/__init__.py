### IMPORTS
### ============================================================================
## Future

## Standard Library
import sys
import warnings

## Installed

## Application
import pythonjsonlogger.json

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


try:
    import msgspec

    MSGSPEC_AVAILABLE = True
except ImportError:
    MSGSPEC_AVAILABLE = False


### DEPRECATED COMPATIBILITY
### ============================================================================
def __getattr__(name: str):
    if name == "jsonlogger":
        warnings.warn(
            "pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json",
            DeprecationWarning,
        )
        return pythonjsonlogger.json
    raise AttributeError(f"module {__name__} has no attribute {name}")
