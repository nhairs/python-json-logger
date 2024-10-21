### IMPORTS
### ============================================================================
## Future

## Standard Library
import warnings

## Installed

## Application
import pythonjsonlogger.json
import pythonjsonlogger.utils

### CONSTANTS
### ============================================================================
ORJSON_AVAILABLE = pythonjsonlogger.utils.package_is_available("orjson")
MSGSPEC_AVAILABLE = pythonjsonlogger.utils.package_is_available("msgspec")


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
