# pylint: disable=missing-function-docstring

### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
import base64
import dataclasses
import datetime
import enum
import sys
from types import TracebackType
from typing import Any
import traceback
import uuid

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

## Installed

## Application


### FUNCTIONS
### ============================================================================
def unknown_default(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    try:
        return repr(obj)
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return "__could_not_encode__"


## Types
## -----------------------------------------------------------------------------
def use_type_default(obj: Any) -> TypeGuard[type]:
    return isinstance(obj, type)


def type_default(obj: type) -> str:
    return obj.__name__


## Dataclasses
## -----------------------------------------------------------------------------
def use_dataclass_default(obj: Any) -> bool:
    return dataclasses.is_dataclass(obj) and not isinstance(obj, type)


def dataclass_default(obj) -> dict[str, Any]:
    return dataclasses.asdict(obj)


## Dates and Times
## -----------------------------------------------------------------------------
def use_time_default(obj: Any) -> TypeGuard[datetime.time]:
    return isinstance(obj, datetime.time)


def time_default(obj: datetime.time) -> str:
    return obj.isoformat()


def use_date_default(obj: Any) -> TypeGuard[datetime.date]:
    return isinstance(obj, datetime.date)


def date_default(obj: datetime.date) -> str:
    return obj.isoformat()


def use_datetime_default(obj: Any) -> TypeGuard[datetime.datetime]:
    return isinstance(obj, datetime.datetime)


def datetime_default(obj: datetime.datetime) -> str:
    return obj.isoformat()


def use_datetime_any(obj: Any) -> TypeGuard[datetime.time | datetime.date | datetime.datetime]:
    return isinstance(obj, (datetime.time, datetime.date, datetime.datetime))


def datetime_any(obj: datetime.time | datetime.date | datetime.date) -> str:
    return obj.isoformat()


## Exception and Tracebacks
## -----------------------------------------------------------------------------
def use_exception_default(obj: Any) -> TypeGuard[BaseException]:
    return isinstance(obj, BaseException)


def exception_default(obj: BaseException) -> str:
    return f"{obj.__class__.__name__}: {obj}"


def use_traceback_default(obj: Any) -> TypeGuard[TracebackType]:
    return isinstance(obj, TracebackType)


def traceback_default(obj: TracebackType) -> str:
    return "".join(traceback.format_tb(obj)).strip()


## Enums
## -----------------------------------------------------------------------------
def use_enum_default(obj: Any) -> TypeGuard[enum.Enum | enum.EnumMeta]:
    return isinstance(obj, (enum.Enum, enum.EnumMeta))


def enum_default(obj: enum.Enum | enum.EnumMeta) -> Any | list[Any]:
    if isinstance(obj, enum.Enum):
        return obj.value
    return [e.value for e in obj]  # type: ignore[var-annotated]


## UUIDs
## -----------------------------------------------------------------------------
def use_uuid_default(obj: Any) -> TypeGuard[uuid.UUID]:
    return isinstance(obj, uuid.UUID)


def uuid_default(obj: uuid.UUID) -> str:
    return str(obj)


## Bytes
## -----------------------------------------------------------------------------
def use_bytes_default(obj: Any) -> TypeGuard[bytes | bytearray]:
    return isinstance(obj, (bytes, bytearray))


def bytes_default(obj: bytes | bytearray, url_safe: bool = True) -> str:
    if url_safe:
        return base64.urlsafe_b64encode(obj).decode("utf8")
    return base64.b64encode(obj).decode("utf8")
