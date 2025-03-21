### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from dataclasses import dataclass
import io
import json
import logging
import logging.config
from typing import Any, Generator

## Installed
import pytest

### SETUP
### ============================================================================
_LOGGER_COUNT = 0
EXT_VAL = 999

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "static_fields": {"ext-val": "ext://tests.test_dictconfig.EXT_VAL"},
        }
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "WARNING", "propagate": False},  # root logger
    },
}


@dataclass
class LoggingEnvironment:
    logger: logging.Logger
    buffer: io.StringIO

    def load_json(self) -> Any:
        return json.loads(self.buffer.getvalue())


@pytest.fixture
def env() -> Generator[LoggingEnvironment, None, None]:
    global _LOGGER_COUNT  # pylint: disable=global-statement
    _LOGGER_COUNT += 1
    logging.config.dictConfig(LOGGING_CONFIG)
    default_formatter = logging.root.handlers[0].formatter
    logger = logging.getLogger(f"pythonjsonlogger.tests.{_LOGGER_COUNT}")
    logger.setLevel(logging.DEBUG)
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(default_formatter)
    logger.addHandler(handler)
    yield LoggingEnvironment(logger=logger, buffer=buffer)
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    buffer.close()
    return


### TESTS
### ============================================================================
def test_external_reference_support(env: LoggingEnvironment):
    env.logger.info("hello")
    log_json = env.load_json()

    assert log_json["ext-val"] == EXT_VAL
    return
