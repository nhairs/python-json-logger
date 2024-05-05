### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library

## Installed
import msgspec.json

## Application
from . import core


### CLASSES
### ============================================================================
class MsgspecFormatter(core.BaseJsonFormatter):
    """JSON formatter using msgspec.json for encoding.

    Refs:
    - https://jcristharif.com/msgspec/api.html#msgspec.json.Encoder
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *args,
        json_default: core.OptionalCallableOrStr = None,
        **kwargs,
    ) -> None:
        """
        Args:
            json_default: a function for encoding non-standard objects see: `msgspec.json.Encode:enc_hook`
        """
        super().__init__(*args, **kwargs)

        self.json_default = core.str_to_object(json_default)
        self._encoder = msgspec.json.Encoder(enc_hook=self.json_default)
        return

    def jsonify_log_record(self, log_record: core.LogRecord) -> str:
        """Returns a json string of the log record."""
        return self._encoder.encode(log_record).decode("utf8")
