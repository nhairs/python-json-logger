### IMPORTS
### ============================================================================
## Future

## Standard Library
import warnings

## Installed

## Application
import pythonjsonlogger.json

### CONSTANTS
### ============================================================================
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
