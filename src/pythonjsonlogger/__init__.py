### IMPORTS
### ============================================================================
## Future

## Standard Library
import warnings

## Installed

## Application
from . import json
from . import utils

### CONSTANTS
### ============================================================================
MSGSPEC_AVAILABLE = utils.package_is_available("msgspec")
ORJSON_AVAILABLE = utils.package_is_available("orjson")
SIMPLEJSON_AVAILABLE = utils.package_is_available("simplejson")
ULTRAJSON_AVAILABLE = utils.package_is_available("ujson")
