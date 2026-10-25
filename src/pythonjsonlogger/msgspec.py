"""JSON Formatter using [`msgspec`](https://github.com/jcrist/msgspec)"""

### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from typing import Any
from collections.abc import Callable

## Installed

## Application
from . import core
from . import defaults as d
from .utils import package_is_available

# We import msgspec after checking it is available
package_is_available("msgspec", throw_error=True)
import msgspec.json  # pylint: disable=wrong-import-position,wrong-import-order


### FUNCTIONS
### ============================================================================
def msgspec_default(obj: Any) -> Any:
    """msgspec default encoder function for non-standard types"""
    if d.use_exception_default(obj):
        return d.exception_default(obj)
    if d.use_traceback_default(obj):
        return d.traceback_default(obj)
    if d.use_enum_default(obj):
        return d.enum_default(obj)
    if d.use_type_default(obj):
        return d.type_default(obj)
    return d.unknown_default(obj)


### CLASSES
### ============================================================================
class MsgspecFormatter(core.BaseJsonFormatter):
    """JSON formatter using [`msgspec.json.Encoder`](https://jcristharif.com/msgspec/api.html#msgspec.json.Encoder) for encoding."""

    def __init__(
        self,
        *args,
        json_default: Callable | None = msgspec_default,
        **kwargs,
    ) -> None:
        """
        Args:
            args: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
            json_default: a function for encoding non-standard objects
            kwargs: see [BaseJsonFormatter][pythonjsonlogger.core.BaseJsonFormatter]
        """
        super().__init__(*args, **kwargs)

        self.json_default = json_default
        self._encoder = msgspec.json.Encoder(enc_hook=self.json_default)
        return

    def jsonify_log_record(self, log_data: core.LogData) -> str:
        """Returns a json string of the log data."""
        return self._encode_log_data(log_data).decode("utf8")

    def _jsonify_log_record_bytes(self, log_data: core.LogData) -> bytes:
        # Preserve custom jsonify_log_record hooks, including overrides using super().
        # The unmodified hook can use native bytes without decoding and re-encoding.
        if (
            getattr(self.jsonify_log_record, "__func__", None)
            is not MsgspecFormatter.jsonify_log_record
        ):
            return super()._jsonify_log_record_bytes(log_data)
        return self._encode_log_data(log_data)

    def _encode_log_data(self, log_data: core.LogData) -> bytes:
        return self._encoder.encode(log_data)
