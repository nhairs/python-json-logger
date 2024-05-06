### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from dataclasses import dataclass
import datetime
import enum
import io
import json
import logging
import sys
import traceback
from types import TracebackType
from typing import Any, Generator
import uuid

if sys.version_info >= (3, 9):
    import zoneinfo
else:
    from backports import zoneinfo

## Installed
from freezegun import freeze_time
import pytest

## Application
import pythonjsonlogger
import pythonjsonlogger.defaults
from pythonjsonlogger.core import RESERVED_ATTRS, BaseJsonFormatter, merge_record_extra
from pythonjsonlogger.json import JsonFormatter

if pythonjsonlogger.ORJSON_AVAILABLE:
    from pythonjsonlogger.orjson import OrjsonFormatter

if pythonjsonlogger.MSGSPEC_AVAILABLE:
    from pythonjsonlogger.msgspec import MsgspecFormatter

### SETUP
### ============================================================================
ALL_FORMATTERS: list[type[BaseJsonFormatter]] = [JsonFormatter]
if pythonjsonlogger.ORJSON_AVAILABLE:
    ALL_FORMATTERS.append(OrjsonFormatter)
if pythonjsonlogger.MSGSPEC_AVAILABLE:
    ALL_FORMATTERS.append(MsgspecFormatter)

_LOGGER_COUNT = 0


@dataclass
class LoggingEnvironment:
    logger: logging.Logger
    buffer: io.StringIO
    handler: logging.Handler

    def set_formatter(self, formatter: BaseJsonFormatter) -> None:
        self.handler.setFormatter(formatter)
        return

    def load_json(self) -> Any:
        return json.loads(self.buffer.getvalue())


@pytest.fixture
def env() -> Generator[LoggingEnvironment, None, None]:
    global _LOGGER_COUNT  # pylint: disable=global-statement
    _LOGGER_COUNT += 1
    logger = logging.getLogger(f"pythonjsonlogger.tests.{_LOGGER_COUNT}")
    logger.setLevel(logging.DEBUG)
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    logger.addHandler(handler)
    yield LoggingEnvironment(logger=logger, buffer=buffer, handler=handler)
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    buffer.close()
    return


def get_traceback_from_exception_followed_by_log_call(env_: LoggingEnvironment) -> str:
    try:
        raise Exception("test")
    except Exception as e:
        env_.logger.exception("hello")
        str_traceback = traceback.format_exc()
        # Formatter removes trailing new line
        if str_traceback.endswith("\n"):
            str_traceback = str_traceback[:-1]
    return str_traceback


class SomeClass:
    def __init__(self, thing: int):
        self.thing = thing
        return


class BrokenClass:
    def __str__(self) -> str:
        raise ValueError("hahah sucker")

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class SomeDataclass:
    things: str
    stuff: int
    junk: bool


try:
    raise ValueError
except ValueError as e:
    STATIC_TRACEBACK = e.__traceback__
    del e


class MultiEnum(enum.Enum):
    NONE = None
    BOOL = False
    STR = "somestring"
    INT = 99
    BYTES = b"some-bytes"


NO_TEST = object()  # Sentinal


### TESTS
### ============================================================================
def test_merge_record_extra():
    record = logging.LogRecord(
        "name", level=1, pathname="", lineno=1, msg="Some message", args=None, exc_info=None
    )
    output = merge_record_extra(record, target={"foo": "bar"}, reserved=[])
    assert output["foo"] == "bar"
    assert output["msg"] == "Some message"
    return


## Common Formatter Tests
## -----------------------------------------------------------------------------
@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_default_format(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_())

    msg = "testing logging format"
    env.logger.info(msg)

    log_json = env.load_json()

    assert log_json["message"] == msg
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_percentage_format(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(
        class_(
            # All kind of different styles to check the regex
            "[%(levelname)8s] %(message)s %(filename)s:%(lineno)d %(asctime)"
        )
    )

    msg = "testing logging format"
    env.logger.info(msg)
    log_json = env.load_json()

    assert log_json["message"] == msg
    assert log_json.keys() == {"levelname", "message", "filename", "lineno", "asctime"}
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_rename_base_field(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_(rename_fields={"message": "@message"}))

    msg = "testing logging format"
    env.logger.info(msg)
    log_json = env.load_json()

    assert log_json["@message"] == msg
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_rename_nonexistent_field(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_(rename_fields={"nonexistent_key": "new_name"}))

    stderr_watcher = io.StringIO()
    sys.stderr = stderr_watcher
    env.logger.info("testing logging rename")
    sys.stderr == sys.__stderr__

    assert "KeyError: 'nonexistent_key'" in stderr_watcher.getvalue()
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_add_static_fields(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_(static_fields={"log_stream": "kafka"}))

    msg = "testing static fields"
    env.logger.info(msg)
    log_json = env.load_json()

    assert log_json["log_stream"] == "kafka"
    assert log_json["message"] == msg
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_format_keys(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    supported_keys = [
        "asctime",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
    ]

    log_format = lambda x: [f"%({i:s})s" for i in x]
    custom_format = " ".join(log_format(supported_keys))

    env.set_formatter(class_(custom_format))

    msg = "testing logging format"
    env.logger.info(msg)
    log_json = env.load_json()

    for key in supported_keys:
        assert key in log_json
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_unknown_format_key(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_("%(unknown_key)s %(message)s"))
    env.logger.info("testing unknown logging format")
    # make sure no error occurs
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_log_dict(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_())

    msg = {"text": "testing logging", "num": 1, 5: "9", "nested": {"more": "data"}}
    env.logger.info(msg)
    log_json = env.load_json()

    assert log_json["text"] == msg["text"]
    assert log_json["num"] == msg["num"]
    assert log_json["5"] == msg[5]
    assert log_json["nested"] == msg["nested"]
    assert log_json["message"] == ""
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_log_extra(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_())

    extra = {"text": "testing logging", "num": 1, 5: "9", "nested": {"more": "data"}}
    env.logger.info("hello", extra=extra)  # type: ignore[arg-type]
    log_json = env.load_json()

    assert log_json["text"] == extra["text"]
    assert log_json["num"] == extra["num"]
    assert log_json["5"] == extra[5]
    assert log_json["nested"] == extra["nested"]
    assert log_json["message"] == "hello"
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_custom_logic_adds_field(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    class CustomJsonFormatter(class_):  # type: ignore[valid-type,misc]

        def process_log_record(self, log_record):
            log_record["custom"] = "value"
            return super().process_log_record(log_record)

    env.set_formatter(CustomJsonFormatter())
    env.logger.info("message")
    log_json = env.load_json()

    assert log_json["custom"] == "value"
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_exc_info(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_())

    expected_value = get_traceback_from_exception_followed_by_log_call(env)
    log_json = env.load_json()

    assert log_json["exc_info"] == expected_value
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_exc_info_renamed(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    env.set_formatter(class_("%(exc_info)s", rename_fields={"exc_info": "stack_trace"}))

    expected_value = get_traceback_from_exception_followed_by_log_call(env)
    log_json = env.load_json()

    assert log_json["stack_trace"] == expected_value
    assert "exc_info" not in log_json
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_custom_object_serialization(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    def encode_complex(z):
        if isinstance(z, complex):
            return (z.real, z.imag)
        raise TypeError(f"Object of type {type(z)} is no JSON serializable")

    env.set_formatter(class_(json_default=encode_complex))  # type: ignore[call-arg]

    env.logger.info("foo", extra={"special": complex(3, 8)})
    log_json = env.load_json()

    assert log_json["special"] == [3.0, 8.0]
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_rename_reserved_attrs(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    log_format = lambda x: [f"%({i:s})s" for i in x]
    reserved_attrs_map = {
        "exc_info": "error.type",
        "exc_text": "error.message",
        "funcName": "log.origin.function",
        "levelname": "log.level",
        "module": "log.origin.file.name",
        "processName": "process.name",
        "threadName": "process.thread.name",
        "msg": "log.message",
    }

    custom_format = " ".join(log_format(reserved_attrs_map.keys()))
    reserved_attrs = [
        attr for attr in RESERVED_ATTRS if attr not in list(reserved_attrs_map.keys())
    ]
    env.set_formatter(
        class_(custom_format, reserved_attrs=reserved_attrs, rename_fields=reserved_attrs_map)
    )

    env.logger.info("message")
    log_json = env.load_json()

    # Note: this check is fragile if we make the following changes in the future (we might):
    # - renaming fields no longer requires the field to be present (#6)
    # - we add the ability (and data above) to rename a field to an existing field name
    #   e.g. {"exc_info": "trace_original", "@custom_trace": "exc_info"}
    for old_name, new_name in reserved_attrs_map.items():
        assert new_name in log_json
        assert old_name not in log_json
    return


@freeze_time(datetime.datetime(2017, 7, 14, 2, 40))
@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_default_encoder_with_timestamp(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    if pythonjsonlogger.ORJSON_AVAILABLE and class_ is OrjsonFormatter:
        # https://github.com/ijl/orjson/issues/481
        pytest.xfail()

    if pythonjsonlogger.MSGSPEC_AVAILABLE and class_ is MsgspecFormatter:
        # https://github.com/jcrist/msgspec/issues/678
        pytest.xfail()

    env.set_formatter(class_(timestamp=True))

    env.logger.info("Hello")
    log_json = env.load_json()

    assert log_json["timestamp"] == "2017-07-14T02:40:00+00:00"
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
@pytest.mark.parametrize(
    ["obj", "type_", "expected"],
    [
        ("somestring", str, "somestring"),
        ("some unicode Привет", str, "some unicode Привет"),
        (1234, int, 1234),
        (1234.5, float, 1234.5),
        (False, bool, False),
        (None, type(None), None),
        (b"some-bytes", str, "c29tZS1ieXRlcw=="),
        (datetime.time(16, 45, 30, 100), str, "16:45:30.000100"),
        (datetime.date(2024, 5, 5), str, "2024-05-05"),
        (datetime.datetime(2024, 5, 5, 16, 45, 30, 100), str, "2024-05-05T16:45:30.000100"),
        (
            datetime.datetime(2024, 5, 5, 16, 45, 30, 100, zoneinfo.ZoneInfo("Australia/Sydney")),
            str,
            "2024-05-05T16:45:30.000100+10:00",
        ),
        (
            uuid.UUID("urn:uuid:12345678-1234-5678-1234-567812345678"),
            str,
            "12345678-1234-5678-1234-567812345678",
        ),
        (Exception, str, "Exception"),
        (Exception("Foo occurred"), str, "Exception: Foo occurred"),
        (BaseException, str, "BaseException"),
        (BaseException("BaseFoo occurred"), str, "BaseException: BaseFoo occurred"),
        (STATIC_TRACEBACK, str, pythonjsonlogger.defaults.traceback_default(STATIC_TRACEBACK)),  # type: ignore[arg-type]
        (
            SomeDataclass(things="le_things", stuff=99, junk=False),
            dict,
            {"things": "le_things", "stuff": 99, "junk": False},
        ),
        (SomeDataclass, str, "SomeDataclass"),
        (SomeClass, str, "SomeClass"),
        (SomeClass(1234), str, NO_TEST),
        (BrokenClass(), str, "__could_not_encode__"),
        (MultiEnum.NONE, type(None), None),
        (MultiEnum.BOOL, bool, MultiEnum.BOOL.value),
        (MultiEnum.STR, str, MultiEnum.STR.value),
        (MultiEnum.INT, int, MultiEnum.INT.value),
        (MultiEnum.BYTES, str, "c29tZS1ieXRlcw=="),
        (MultiEnum, list, [None, False, "somestring", 99, "c29tZS1ieXRlcw=="]),
    ],
)
def test_common_types_encoded(
    env: LoggingEnvironment,
    class_: type[BaseJsonFormatter],
    obj: object,
    type_: type,
    expected: Any,
):
    ## Known bad cases
    if class_ is JsonFormatter:
        if False:
            pytest.xfail()

    if pythonjsonlogger.ORJSON_AVAILABLE and class_ is OrjsonFormatter:
        if False:
            pytest.xfail()

    if pythonjsonlogger.MSGSPEC_AVAILABLE and class_ is MsgspecFormatter:
        if obj is SomeDataclass or (
            isinstance(obj, enum.Enum) and obj in {MultiEnum.BYTES, MultiEnum.NONE, MultiEnum.BOOL}
        ):
            pytest.xfail()

    ## Test
    env.set_formatter(class_())
    extra = {
        "extra": obj,
        "extra_dict": {"item": obj},
        "extra_list": [obj],
    }
    env.logger.info("hello", extra=extra)
    log_json = env.load_json()

    assert isinstance(log_json["extra"], type_)
    assert isinstance(log_json["extra_dict"]["item"], type_)
    assert isinstance(log_json["extra_list"][0], type_)

    if expected is NO_TEST:
        return

    if expected is None or isinstance(expected, bool):
        assert log_json["extra"] is expected
        assert log_json["extra_dict"]["item"] is expected
        assert log_json["extra_list"][0] is expected
    else:
        assert log_json["extra"] == expected
        assert log_json["extra_dict"]["item"] == expected
        assert log_json["extra_list"][0] == expected
    return


@pytest.mark.parametrize("class_", ALL_FORMATTERS)
def test_custom_default(env: LoggingEnvironment, class_: type[BaseJsonFormatter]):
    def custom_default(obj):
        if isinstance(obj, SomeClass):
            return {"TYPE": obj.thing}
        return None

    env.set_formatter(class_(json_default=custom_default))  # type: ignore[call-arg]
    env.logger.info("hello", extra={"extra": SomeClass(999)})
    log_json = env.load_json()

    assert log_json["extra"] == {"TYPE": 999}
    return


## JsonFormatter Specific
## -----------------------------------------------------------------------------
def test_json_ensure_ascii_true(env: LoggingEnvironment):
    env.set_formatter(JsonFormatter())
    env.logger.info("Привет")

    # Note: we don't use env.load_json as we want to know the raw output
    msg = env.buffer.getvalue().split('"message": "', 1)[1].split('"', 1)[0]
    assert msg == r"\u041f\u0440\u0438\u0432\u0435\u0442"
    return


def test_json_ensure_ascii_false(env: LoggingEnvironment):
    env.set_formatter(JsonFormatter(json_ensure_ascii=False))
    env.logger.info("Привет")

    # Note: we don't use env.load_json as we want to know the raw output
    msg = env.buffer.getvalue().split('"message": "', 1)[1].split('"', 1)[0]
    assert msg == "Привет"
    return
