"""Opt-in formatter benchmarks; setup and correctness checks are not timed."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
import json
import logging
import sys
from typing import Any
from uuid import UUID

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pythonjsonlogger.core import BaseJsonFormatter

FORMATTERS = {"json": "JsonFormatter", "orjson": "OrjsonFormatter", "msgspec": "MsgspecFormatter"}


@dataclass
class Request:
    """A small application object for native and fallback encoding paths."""

    method: str
    status: int


@dataclass
class Workload:
    """Prepared payload and expectations for one parametrized workload."""

    name: str
    data: dict[str, Any]
    expected: dict[str, Any] | None = None
    scalar_message: bool = False
    exc_info: Any = None


def simple() -> Workload:
    """A short string message."""
    return Workload("simple", {"message": "request completed"}, scalar_message=True)


def structured() -> Workload:
    """A string message with scalar LogRecord extras."""
    return Workload(
        "structured",
        {
            "message": "request completed",
            "request_id": "req-123",
            "status": 200,
            "elapsed": 0.125,
            "cached": False,
            "error": None,
        },
        scalar_message=True,
    )


def nested() -> Workload:
    """A dictionary message containing 100 nested objects."""
    return Workload(
        "nested",
        {
            "message": "request completed",
            "items": [
                {"id": i, "tags": ["alpha", "beta"], "metrics": {"count": i, "ok": True}}
                for i in range(100)
            ],
        },
    )


def unicode_message() -> Workload:
    """A dictionary message with accented text, Japanese text, and emoji."""
    return Workload("unicode", {"message": "Request café — 東京 🌍 " * 20})


def rich() -> Workload:
    """A UTC datetime, UUID, and dataclass with explicit serialized expectations."""
    return Workload(
        "rich",
        {
            "message": "request completed",
            "timestamp": datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            "request_id": UUID("12345678-1234-5678-1234-567812345678"),
            "request": Request("GET", 200),
        },
        expected={
            "message": "request completed",
            "timestamp": "2024-01-02T03:04:05+00:00",
            "request_id": "12345678-1234-5678-1234-567812345678",
            "request": {"method": "GET", "status": 200},
        },
    )


def exception() -> Workload:
    """A prepared traceback, rendered inside each full formatting operation."""
    try:
        raise ValueError("invalid request")
    except ValueError:
        exc_info = sys.exc_info()
    return Workload(
        "exception",
        {
            "message": "request completed",
            "exc_info": logging.Formatter().formatException(exc_info),
        },
        scalar_message=True,
        exc_info=exc_info,
    )


@pytest.mark.parametrize("backend", FORMATTERS)
@pytest.mark.parametrize(
    "workload",
    (
        pytest.param(simple, id="simple"),
        pytest.param(structured, id="structured"),
        pytest.param(nested, id="nested"),
        pytest.param(unicode_message, id="unicode"),
        pytest.param(rich, id="rich"),
        pytest.param(exception, id="exception"),
    ),
)
@pytest.mark.parametrize("layer", ("serialization", "formatting"))
def test_formatter(
    benchmark: BenchmarkFixture, backend: str, workload: Callable[[], Workload], layer: str
) -> None:
    """Measure steady-state encoding or formatting with default formatter settings."""
    if backend != "json":
        pytest.importorskip(backend)
    formatter: BaseJsonFormatter = getattr(
        import_module(f"pythonjsonlogger.{backend}"), FORMATTERS[backend]
    )()
    case = workload()
    expected = (case.expected if case.expected is not None else case.data).copy()
    if backend == "msgspec" and case.name == "rich":
        expected["timestamp"] = "2024-01-02T03:04:05Z"
    message = case.data["message"] if case.scalar_message else case.data.copy()
    record = logging.LogRecord(
        "benchmark", logging.INFO, "application.py", 42, message, (), case.exc_info
    )
    if case.scalar_message:
        record.__dict__.update(
            {key: value for key, value in case.data.items() if key not in ("message", "exc_info")}
        )
    operation: Callable[[Any], str] = (
        formatter.jsonify_log_record if layer == "serialization" else formatter.format
    )
    argument: Any = case.data if layer == "serialization" else record
    first = operation(argument)
    assert json.loads(first) == expected
    assert operation(argument) == first
    benchmark.extra_info.update(
        backend=backend, workload=case.name, layer=layer, output_bytes=len(first.encode("utf8"))
    )
    result = benchmark(operation, argument)
    assert result == first
    assert json.loads(result) == expected
    return
