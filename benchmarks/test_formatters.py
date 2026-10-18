"""Opt-in formatter benchmarks; setup and correctness checks are not timed."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any
from uuid import UUID

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from pythonjsonlogger.json import JsonFormatter
from pythonjsonlogger.msgspec import MsgspecFormatter
from pythonjsonlogger.orjson import OrjsonFormatter

FORMATTERS = {
    "json": JsonFormatter,
    "orjson": OrjsonFormatter,
    "msgspec": MsgspecFormatter,
}
WORKLOADS = ("simple", "structured", "nested", "unicode", "rich", "exception")


@dataclass
class Request:
    """A small application object for native and fallback encoding paths."""

    method: str
    status: int


def prepare(workload: str, backend: str) -> tuple[dict[str, Any], logging.LogRecord, dict]:
    """Build equivalent serialization data, a record, and explicit expected output."""
    data: dict[str, Any] = {"message": "request completed"}
    expected: dict[str, Any] = dict(data)
    exc_info = None
    if workload == "structured":
        data.update(request_id="req-123", status=200, elapsed=0.125, cached=False, error=None)
        expected = dict(data)
    elif workload == "nested":
        data["items"] = [
            {"id": i, "tags": ["alpha", "beta"], "metrics": {"count": i, "ok": True}}
            for i in range(100)
        ]
        expected = dict(data)
    elif workload == "unicode":
        data["message"] = "Request café — 東京 🌍 " * 20
        expected = dict(data)
    elif workload == "rich":
        data.update(
            timestamp=datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            request_id=UUID("12345678-1234-5678-1234-567812345678"),
            request=Request("GET", 200),
        )
        expected.update(
            timestamp=(
                "2024-01-02T03:04:05Z" if backend == "msgspec" else "2024-01-02T03:04:05+00:00"
            ),
            request_id="12345678-1234-5678-1234-567812345678",
            request={"method": "GET", "status": 200},
        )
    elif workload == "exception":
        try:
            raise ValueError("invalid request")
        except ValueError:
            exc_info = sys.exc_info()
        data["exc_info"] = logging.Formatter().formatException(exc_info)
        expected = dict(data)

    # Scalar extras exercise LogRecord extras; nested/rich data exercise dictionary messages.
    message: Any = data.copy()
    if workload in ("simple", "structured", "exception"):
        message = data["message"]
    record = logging.LogRecord(
        "benchmark", logging.INFO, "application.py", 42, message, (), exc_info
    )
    if workload == "structured":
        record.__dict__.update({key: value for key, value in data.items() if key != "message"})
    return data, record, expected


@pytest.mark.parametrize("backend", FORMATTERS)
@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("layer", ("serialization", "formatting"))
def test_formatter(benchmark: BenchmarkFixture, backend: str, workload: str, layer: str) -> None:
    """Measure steady-state encoding or formatting with default formatter settings."""
    formatter = FORMATTERS[backend]()
    data, record, expected = prepare(workload, backend)
    operation: Callable[[Any], str] = (
        formatter.jsonify_log_record if layer == "serialization" else formatter.format
    )
    argument: Any = data if layer == "serialization" else record
    first = operation(argument)
    assert json.loads(first) == expected
    assert operation(argument) == first
    benchmark.extra_info.update(
        backend=backend, workload=workload, layer=layer, output_bytes=len(first.encode("utf8"))
    )
    result = benchmark(operation, argument)
    assert result == first
    assert json.loads(result) == expected
    return
