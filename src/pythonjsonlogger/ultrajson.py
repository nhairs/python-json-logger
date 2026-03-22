"""JSON Formatter using [ultrajson](https://github.com/ultrajson/ultrajson)"""

### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from typing import Any, Optional, Callable

## Installed

## Application
from . import core
from . import defaults as d
from .utils import package_is_available

# We import ujson after checking it is available
package_is_available("ujson", throw_error=True)
import ujson  # pylint: disable=wrong-import-position,wrong-import-order


### FUNCTIONS
### ============================================================================
def ujson_default(obj: Any) -> Any:
    """ujson default encoder function for non-standard types"""

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
class UltraJsonFormatter(core.BaseJsonFormatter):
    """JSON formatter using [ultrajson](https://github.com/ultrajson/ultrajson) (`ujson`) for encoding.

    !!! warning "UltraJSON is in maintenance mode"
        [Per README](https://github.com/ultrajson/ultrajson/tree/main?tab=readme-ov-file#project-status) users
        are encouraged to move to another JSON encoder such as `orjson`.

    !!! warning "Note that ultrajson handles certain input different to other encoders in python-json-logger."

        `datetime.datetime` objects use `' '` as the delimiter instead of `'T'`.

        `bytes` can only be encoded if they are valid `utf-8`.


    """

    def __init__(
        self,
        *args,
        json_default: Optional[Callable] = ujson_default,
        json_indent: int = 0,
        **kwargs,
    ) -> None:
        """
        Args:
            args: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
            json_default: a function for encoding non-standard objects
            json_indent: indent output with this number of spaces.
            kwargs: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
        """
        super().__init__(*args, **kwargs)

        self.json_default = json_default
        self.json_indent = json_indent

        return

    def jsonify_log_record(self, log_data: core.LogData) -> str:
        """Returns a json string of the log data."""
        return ujson.dumps(
            log_data, indent=self.json_indent, default=self.json_default, reject_bytes=False
        )
