from __future__ import annotations

from typing import List, Type

import pythonjsonlogger  # To access ORJSON_AVAILABLE and MSGSPEC_AVAILABLE
from pythonjsonlogger.core import BaseJsonFormatter
from pythonjsonlogger.json import JsonFormatter

ALL_FORMATTERS: List[Type[BaseJsonFormatter]] = [JsonFormatter]

if pythonjsonlogger.ORJSON_AVAILABLE:
    from pythonjsonlogger.orjson import OrjsonFormatter

    ALL_FORMATTERS.append(OrjsonFormatter)

if pythonjsonlogger.MSGSPEC_AVAILABLE:
    from pythonjsonlogger.msgspec import MsgspecFormatter

    ALL_FORMATTERS.append(MsgspecFormatter)

ALL_FORMATTER_PATHS: List[str] = [f"{cls.__module__}.{cls.__name__}" for cls in ALL_FORMATTERS]
