### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from typing import Any

## Installed
import orjson

## Application
from . import core
from . import defaults as d


### FUNCTIONS
### ============================================================================
def orjson_default(obj: Any) -> Any:
    """orjson default encoder function for non-standard types"""
    if d.use_exception_default(obj):
        return d.exception_default(obj)
    if d.use_traceback_default(obj):
        return d.traceback_default(obj)
    if d.use_bytes_default(obj):
        return d.bytes_default(obj)
    if d.use_enum_default(obj):
        return d.enum_default(obj)
    if d.use_type_default(obj):
        return d.type_default(obj)
    return d.unknown_default(obj)


### CLASSES
### ============================================================================
class OrjsonFormatter(core.BaseJsonFormatter):
    """JSON formatter using orjson for encoding.

    Refs:
    - https://github.com/ijl/orjson
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *args,
        json_default: core.OptionalCallableOrStr = orjson_default,
        json_indent: bool = False,
        **kwargs,
    ) -> None:
        """
        Args:
            json_default: a function for encoding non-standard objects see:
                https://github.com/ijl/orjson#default
            json_indent: indent output with 2 spaces. see:
                https://github.com/ijl/orjson#opt_indent_2
        """
        super().__init__(*args, **kwargs)

        self.json_default = core.str_to_object(json_default)
        self.json_indent = json_indent
        return

    def jsonify_log_record(self, log_record: core.LogRecord) -> str:
        """Returns a json string of the log record."""
        opt = orjson.OPT_NON_STR_KEYS
        if self.json_indent:
            opt |= orjson.OPT_INDENT_2

        return orjson.dumps(log_record, default=self.json_default, option=opt).decode("utf8")
