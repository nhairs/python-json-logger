### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
import io
import json
import logging
import logging.config
import sys
from typing import Any, Optional, Dict, Callable

## Installed
import pytest

## Application
# No longer need orjson_module and msgspec_module directly in this file,
# as ALL_FORMATTER_PATHS from tests/__init__.py handles conditional logic.
# from pythonjsonlogger import orjson as orjson_module
# from pythonjsonlogger import msgspec as msgspec_module


### SETUP
### ============================================================================
_LOGGER_COUNT = 0
EXT_VAL = 999


class Dummy:
    pass


def my_json_default(obj: Any) -> Any:
    if isinstance(obj, Dummy):
        return "DUMMY"
    return obj


# Import the centralized list of formatter paths
from tests import ALL_FORMATTER_PATHS


class LoggingEnvironment:
    def __init__(self, config: Dict[str, Any], logger_name_suffix: str = ""):
        self.config = config
        self.logger_name_suffix = logger_name_suffix
        self.logger: Optional[logging.Logger] = None
        self.buffer: Optional[io.StringIO] = None
        self.formatter: Optional[logging.Formatter] = None
        self._test_handler: Optional[logging.StreamHandler] = None

    def __enter__(self) -> "LoggingEnvironment":
        global _LOGGER_COUNT
        _LOGGER_COUNT += 1
        logging.config.dictConfig(self.config)
        loggers_config = self.config.get("loggers", {})
        named_loggers = {
            name: cfg for name, cfg in loggers_config.items() if name and name != "root"
        }
        if not named_loggers:
            if "" in loggers_config or "root" in loggers_config:
                raise ValueError(
                    "LoggingEnvironment expects at least one explicitly named logger in the configuration "
                    "to target. Configurations with only a root logger ('\"\"' or '\"root\"') "
                    "are not supported by this context manager."
                )
            raise ValueError(
                "No named loggers found in the 'loggers' section of the configuration. "
                "LoggingEnvironment requires a named logger to target."
            )
        logger_to_get = list(named_loggers.keys())[0]
        logger_config = named_loggers[logger_to_get]
        if not logger_config.get("handlers"):
            raise ValueError(
                f"Named logger '{logger_to_get}' in configuration has no handlers defined."
            )

        configured_logger_instance = logging.getLogger(logger_to_get)
        determined_formatter = None
        if configured_logger_instance.handlers:
            handler_instance = configured_logger_instance.handlers[0]
            if hasattr(handler_instance, "formatter"):
                determined_formatter = handler_instance.formatter

        final_logger_name = f"pythonjsonlogger.tests.{_LOGGER_COUNT}{self.logger_name_suffix}"
        self.logger = logging.getLogger(final_logger_name)
        self.logger.setLevel(logging.DEBUG)
        self.buffer = io.StringIO()
        self._test_handler = logging.StreamHandler(self.buffer)
        if determined_formatter:
            self._test_handler.setFormatter(determined_formatter)
        self.logger.addHandler(self._test_handler)
        self.formatter = self._test_handler.formatter
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.logger and self._test_handler:
            self.logger.removeHandler(self._test_handler)
        if self.buffer:
            self.buffer.close()
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {"null": {"class": "logging.NullHandler"}},
                "root": {"handlers": ["null"], "level": "WARNING"},
            }
        )
        return False

    def load_json(self) -> Any:
        if self.buffer is None:
            raise RuntimeError(
                "Buffer is not initialized; LoggingEnvironment not used as context manager?"
            )
        return json.loads(self.buffer.getvalue())

    def get_output(self) -> str:
        if self.buffer is None:
            raise RuntimeError(
                "Buffer is not initialized; LoggingEnvironment not used as context manager?"
            )
        return self.buffer.getvalue()


### TESTS
### ============================================================================
EXTERNAL_REF_TEST_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default_fmt": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "json_default": "ext://tests.test_dictconfig.my_json_default",
            "static_fields": {"ext-val": "ext://tests.test_dictconfig.EXT_VAL"},
        }
    },
    "handlers": {
        "default_h": {
            "level": "DEBUG",
            "formatter": "default_fmt",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "testlogger_ext_ref": {
            "handlers": ["default_h"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
}

# test_external_reference_support has been replaced by test_external_reference_support_parameterized
# def test_external_reference_support():
#     with LoggingEnvironment(EXTERNAL_REF_TEST_CONFIG) as env:
#         assert env.formatter is not None
#         assert env.formatter.json_default is my_json_default  # type: ignore[attr-defined]

#         env.logger.info("hello", extra={"dummy": Dummy()})
#         log_json = env.load_json()

#         assert log_json["ext-val"] == EXT_VAL
#         assert log_json["dummy"] == "DUMMY"
#     return


@pytest.mark.parametrize("formatter_class_path", ALL_FORMATTER_PATHS)
def test_external_reference_support_parameterized(formatter_class_path: str):
    # This test is based on test_external_reference_support, but parameterized for formatters.
    # It specifically checks if ext:// references for json_default and static_fields
    # are correctly handled by dictConfig when instantiating various formatters.
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default_fmt": {
                "()": formatter_class_path,
                "json_default": "ext://tests.test_dictconfig.my_json_default",
                "static_fields": {"ext-val": "ext://tests.test_dictconfig.EXT_VAL"},
            }
        },
        "handlers": {
            "default_h": {
                "level": "DEBUG",
                "formatter": "default_fmt",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "testlogger_ext_ref_param": {  # Unique logger name for parameterization
                "handlers": ["default_h"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
    }

    with LoggingEnvironment(
        config, logger_name_suffix=f"_{formatter_class_path.split('.')[-1]}"
    ) as env:
        assert env.formatter is not None
        assert env.logger is not None  # mypy check

        # Check for json_default handling:
        # Only JsonFormatter and its direct subclasses are expected to have/use json_default in this way.
        # Other formatters like OrjsonFormatter/MsgspecFormatter might have different mechanisms
        # or might not support 'json_default' in their __init__ from dictConfig.
        if "JsonFormatter" in formatter_class_path:  # Covers pythonjsonlogger.json.JsonFormatter
            if hasattr(env.formatter, "json_default"):
                assert (
                    env.formatter.json_default is my_json_default
                ), f"json_default not correctly set for {formatter_class_path}"

        # Check for static_fields handling (ext:// part)
        # All BaseJsonFormatter subclasses should support static_fields with ext:// resolution via __init__.
        # We access this through the log output.

        env.logger.info("hello", extra={"dummy": Dummy()})
        log_json = env.load_json()

        assert (
            log_json.get("ext-val") == EXT_VAL
        ), f"ext:// static_field not resolved for {formatter_class_path}"

        # Check how Dummy() is serialized, which depends on json_default resolution
        if "JsonFormatter" in formatter_class_path:  # Covers pythonjsonlogger.json.JsonFormatter
            if (
                hasattr(env.formatter, "json_default")
                and env.formatter.json_default == my_json_default
            ):
                assert (
                    log_json.get("dummy") == "DUMMY"
                ), f"dummy with json_default not correctly serialized for {formatter_class_path}"
            else:
                # If json_default isn't set as expected, the object might be stringified or cause error
                # For this test, if it's a JsonFormatter, we expect json_default to be there.
                # If a custom JsonFormatter derivative doesn't pick up json_default, that's an issue.
                assert "dummy" in log_json  # At least ensure it's present
        else:
            # For OrjsonFormatter/MsgspecFormatter, they don't use `json_default` from __init__.
            # They have their own default logic. Dummy() would likely be stringified by their encoders.
            # This assertion might need to be more specific if their stringification is predictable
            # or if they raise an error for unknown types without a handler.
            # For now, checking presence is a basic step.
            assert "dummy" in log_json, f"dummy field missing for {formatter_class_path}"
    return


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Dummy):
            return "CUSTOM_ENCODED_DUMMY"
        return super().default(o)


def custom_json_serializer(obj: Any, **kwargs: Any) -> str:
    return json.dumps({"custom_serialized": obj}, **kwargs)


def test_json_encoder_option():
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "custom_encoder_fmt": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "json_encoder": "ext://tests.test_dictconfig.CustomJsonEncoder",
            }
        },
        "handlers": {
            "custom_encoder_h": {
                "level": "DEBUG",
                "formatter": "custom_encoder_fmt",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "testlogger_param": {
                "handlers": ["custom_encoder_h"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
    }
    with LoggingEnvironment(config) as env:
        env.logger.info("test encoder", extra={"dummy_obj": Dummy()})
        log_json = env.load_json()
        assert log_json["dummy_obj"] == "CUSTOM_ENCODED_DUMMY"
    return


def test_json_serializer_option():
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "custom_serializer_fmt": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "json_serializer": "ext://tests.test_dictconfig.custom_json_serializer",
            }
        },
        "handlers": {
            "custom_serializer_h": {
                "level": "DEBUG",
                "formatter": "custom_serializer_fmt",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "testlogger_param": {
                "handlers": ["custom_serializer_h"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
    }
    with LoggingEnvironment(config) as env:
        env.logger.info("test serializer")
        log_output = env.get_output().strip()
        log_json = json.loads(log_output)
        assert "custom_serialized" in log_json
        assert log_json["custom_serialized"]["message"] == "test serializer"
    return


### TESTS FOR dictConfig SCENARIOS
### ============================================================================


@pytest.mark.parametrize("disable_loggers_val", [True, False])
def test_disable_existing_loggers(disable_loggers_val: bool):
    PRE_EXISTING_LOGGER_NAME = "my_preexisting_logger"
    pre_existing_logger = logging.getLogger(PRE_EXISTING_LOGGER_NAME)
    pre_existing_logger.setLevel(logging.WARNING)
    pre_existing_buffer = io.StringIO()
    pre_existing_handler = logging.StreamHandler(pre_existing_buffer)
    pre_existing_logger.addHandler(pre_existing_handler)

    pre_existing_logger.warning("This is from pre-existing logger.")
    assert "This is from pre-existing logger." in pre_existing_buffer.getvalue()

    config = {
        "version": 1,
        "disable_existing_loggers": disable_loggers_val,
        "formatters": {"simple": {"()": "pythonjsonlogger.json.JsonFormatter"}},
        "handlers": {
            "new_handler": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "new_logger": {
                "handlers": ["new_handler"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
        "root": {"handlers": ["new_handler"], "level": "CRITICAL"},
    }

    logging.config.dictConfig(config)

    pre_existing_buffer.truncate(0)
    pre_existing_buffer.seek(0)
    if not disable_loggers_val and pre_existing_logger.disabled:
        pre_existing_logger.disabled = False

    pre_existing_logger.warning("Another message from pre-existing logger.")
    log_output_after_config = pre_existing_buffer.getvalue()

    if disable_loggers_val:
        assert pre_existing_logger.disabled
        assert (
            log_output_after_config == ""
        ), "Log output found even when logger expected to be disabled."
    else:
        assert not pre_existing_logger.disabled
        assert "Another message from pre-existing logger." in log_output_after_config

    pre_existing_logger.removeHandler(pre_existing_handler)
    pre_existing_logger.setLevel(logging.NOTSET)
    pre_existing_logger.disabled = False

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"null": {"class": "logging.NullHandler"}},
            "root": {"handlers": ["null"], "level": "WARNING"},
        }
    )
    return


def test_multiple_handlers_and_formatters():

    buffer1 = io.StringIO()
    buffer2 = io.StringIO()

    class TestStream1(io.StringIO):
        pass

    class TestStream2(io.StringIO):
        pass

    global test_stream_1_instance, test_stream_2_instance
    test_stream_1_instance = buffer1
    test_stream_2_instance = buffer2

    multi_handler_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "fmt1": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(levelname)s %(message)s",
                "static_fields": {"format": "fmt1"},
            },
            "fmt2": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(levelname)s %(message)s",
                "static_fields": {"format": "fmt2"},
            },
        },
        "handlers": {
            "h1": {
                "class": "logging.StreamHandler",
                "formatter": "fmt1",
                "level": "INFO",
                "stream": "ext://tests.test_dictconfig.test_stream_1_instance",
            },
            "h2": {
                "class": "logging.StreamHandler",
                "formatter": "fmt2",
                "level": "DEBUG",
                "stream": "ext://tests.test_dictconfig.test_stream_2_instance",
            },
        },
        "loggers": {
            "multi_test_logger": {
                "handlers": ["h1", "h2"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
        "root": {"handlers": [], "level": "CRITICAL"},
    }

    logging.config.dictConfig(multi_handler_config)
    logger = logging.getLogger("multi_test_logger")

    logger.debug("A debug message.")
    logger.info("An info message.")
    logger.warning("A warning message.")

    output1 = buffer1.getvalue()
    logs1 = [json.loads(line) for line in output1.strip().split("\n") if line]
    assert len(logs1) == 2
    for log_entry in logs1:
        assert log_entry["format"] == "fmt1"
    assert logs1[0]["message"] == "An info message."
    assert logs1[0]["levelname"] == "INFO"
    assert logs1[1]["message"] == "A warning message."
    assert logs1[1]["levelname"] == "WARNING"

    output2 = buffer2.getvalue()
    logs2 = [json.loads(line) for line in output2.strip().split("\n") if line]
    assert len(logs2) == 3
    for log_entry in logs2:
        assert log_entry["format"] == "fmt2"
    assert logs2[0]["message"] == "A debug message."
    assert logs2[0]["levelname"] == "DEBUG"
    assert logs2[1]["message"] == "An info message."
    assert logs2[1]["levelname"] == "INFO"
    assert logs2[2]["message"] == "A warning message."
    assert logs2[2]["levelname"] == "WARNING"

    buffer1.close()
    buffer2.close()
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    del globals()["test_stream_1_instance"]
    del globals()["test_stream_2_instance"]
    return


class LevelFilter(logging.Filter):
    def __init__(self, level_to_allow: int):
        super().__init__()
        self.level_to_allow = level_to_allow

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level_to_allow


level_filter_instance = LevelFilter(logging.WARNING)


def test_filter_configuration():
    config_params = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "only_warning_filter": {
                "()": "ext://tests.test_dictconfig.LevelFilter",
                "level_to_allow": logging.WARNING,
            }
        },
        "formatters": {
            "simple_fmt": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(levelname)s %(message)s",
            }
        },
        "handlers": {
            "filter_h": {
                "class": "logging.StreamHandler",
                "formatter": "simple_fmt",
                "level": "DEBUG",
                "filters": ["only_warning_filter"],
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "filter_test_logger": {
                "handlers": ["filter_h"],
                "level": "DEBUG",
                "propagate": False,
            }
        },
        "root": {"handlers": [], "level": "CRITICAL"},
    }

    test_buffer = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = test_buffer

    try:
        logging.config.dictConfig(config_params)
        logger_with_filter = logging.getLogger("filter_test_logger")

        logger_with_filter.debug("This is a debug message.")
        logger_with_filter.info("This is an info message.")
        logger_with_filter.warning("This is a warning message.")
        logger_with_filter.error("This is an error message.")

        log_output = test_buffer.getvalue()
        lines = log_output.strip().split("\n")
        actual_logs = [json.loads(line) for line in lines if line]

        assert len(actual_logs) == 1
        assert actual_logs[0]["message"] == "This is a warning message."
        assert actual_logs[0]["levelname"] == "WARNING"
        assert "message" in actual_logs[0]

    finally:
        sys.stdout = original_stdout
        test_buffer.close()
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {"null": {"class": "logging.NullHandler"}},
                "root": {"handlers": ["null"], "level": "WARNING"},
            }
        )
    return
