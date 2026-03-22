"""JSON Formatter using [simplejson](https://github.com/simplejson/simplejson/tree/master)"""

### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from typing import Any, Optional, Union, Callable

## Installed

## Application
from . import core
from . import defaults as d
from .utils import package_is_available

# We import simplejson after checking it is available
package_is_available("simplejson", throw_error=True)
import simplejson  # pylint: disable=wrong-import-position,wrong-import-order


### FUNCTIONS
### ============================================================================
def simplejson_default(obj: Any) -> Any:
    """simplejson default encoder function for non-standard types"""
    if d.use_exception_default(obj):
        return d.exception_default(obj)

    if d.use_traceback_default(obj):
        return d.traceback_default(obj)

    if d.use_enum_default(obj):
        return d.enum_default(obj)

    if d.use_dataclass_default(obj):
        return d.dataclass_default(obj)

    if d.use_type_default(obj):
        return d.type_default(obj)

    return d.unknown_default(obj)


### CLASSES
### ============================================================================
class SimpleJsonFormatter(core.BaseJsonFormatter):
    """JSON formatter using [simplejson](https://github.com/simplejson/simplejson/tree/master) for encoding.

    !!! warning "Note that simplejson handles certain input different to other encoders in python-json-logger."

        `datetime.datetime` objects use `' '` as the delimiter instead of `'T'`.

        `bytes` can only be encoded if they are valid `utf-8`.


    """

    def __init__(
        self,
        *args,
        json_default: Optional[Callable] = simplejson_default,
        json_indent: Optional[Union[int, str]] = None,
        **kwargs,
    ) -> None:
        """
        Args:
            args: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
            json_default: a function for encoding non-standard objects
            json_indent: indent output with this number of spaces or with the given string.
            kwargs: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
        """
        super().__init__(*args, **kwargs)

        # TODO: consider supporting for_json
        # REF: https://github.com/simplejson/simplejson/blob/master/simplejson/encoder.py#L220

        self.json_encoder = simplejson.JSONEncoder(
            default=json_default,
            indent=json_indent,
        )
        return

    def jsonify_log_record(self, log_data: core.LogData) -> str:
        """Returns a json string of the log data."""
        return self.json_encoder.encode(log_data)
