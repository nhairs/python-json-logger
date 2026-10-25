"""JSON HTTP transport, failure isolation, and session ownership tests."""

from __future__ import annotations

from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import logging
import logging.config
from queue import Queue
import subprocess
import sys
from threading import Thread
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from pythonjsonlogger.exception import MissingPackageError
from pythonjsonlogger.http import JsonHttpHandler
from pythonjsonlogger.json import JsonFormatter


@pytest.fixture
def transport() -> tuple[Mock, Mock]:
    response = Mock()
    session = Mock()
    session.request.return_value = response
    return session, response


def test_exact_request_options_and_copying(transport: tuple[Mock, Mock]):
    session, response = transport
    headers = {"Authorization": "Bearer test"}
    options = {"headers": headers, "timeout": 12, "auth": ("name", "password")}
    handler = JsonHttpHandler("https://example.test/logs", session=session, request_kwargs=options)
    handler.setFormatter(JsonFormatter(json_ensure_ascii=False, json_indent=2))
    record = logging.makeLogRecord({"msg": "雪"})
    handler.handle(record)
    session.request.assert_called_once_with(
        "POST",
        "https://example.test/logs",
        data=b'{\n  "message": "\xe9\x9b\xaa"\n}',
        headers={**headers, "Content-Type": "application/json"},
        timeout=12,
        auth=("name", "password"),
    )
    assert headers == {"Authorization": "Bearer test"}
    assert options["headers"] is headers
    response.raise_for_status.assert_called_once_with()
    response.close.assert_called_once_with()
    handler.close()
    session.close.assert_not_called()
    return


@pytest.mark.parametrize("method", ["POST", "post", "PUT", "put"])
def test_methods_defaults_and_reuse(method: str, transport: tuple[Mock, Mock]):
    session, _ = transport
    handler = JsonHttpHandler("https://example.test/logs", method=method, session=session)
    record = logging.makeLogRecord({"msg": "hello"})
    handler.handle(record)
    handler.handle(record)
    assert session.request.call_count == 2
    assert session.request.call_args.args == (method.upper(), "https://example.test/logs")
    assert session.request.call_args.kwargs == {
        "data": b'{"message": "hello"}',
        "headers": {"Content-Type": "application/json"},
        "timeout": 5,
    }
    handler.close()
    handler.handle(record)
    assert session.request.call_count == 2
    return


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE", ""])
def test_invalid_method(method: str):
    with pytest.raises(ValueError, match="method"):
        JsonHttpHandler("https://example.test", method=method)
    return


@pytest.mark.parametrize("key", ["data", "json", "files", "method", "url"])
def test_conflicting_options(key: str):
    with pytest.raises(ValueError, match=key):
        JsonHttpHandler("https://example.test", request_kwargs={key: None})
    return


def test_header_and_timeout_overrides(transport: tuple[Mock, Mock]):
    session, _ = transport
    handler = JsonHttpHandler(
        "https://example.test",
        session=session,
        request_kwargs={"headers": {"content-TYPE": "application/custom+json"}, "timeout": None},
    )
    handler.handle(logging.makeLogRecord({"msg": "hello"}))
    assert session.request.call_args.kwargs["headers"] == {
        "content-TYPE": "application/custom+json"
    }
    assert session.request.call_args.kwargs["timeout"] is None
    handler.close()
    return


@pytest.mark.parametrize("prefix", ["", "prefix: ", "雪: "])
def test_prefix_is_transmitted_unchanged(prefix: str, transport: tuple[Mock, Mock]):
    session, _ = transport
    handler = JsonHttpHandler("https://example.test", session=session)
    handler.setFormatter(JsonFormatter(prefix=prefix))
    handler.handle(logging.makeLogRecord({"msg": "hello"}))
    assert session.request.call_args.kwargs["data"] == (prefix + '{"message": "hello"}').encode(
        "utf8"
    )
    handler.close()
    return


def test_ordinary_and_legacy_formatters(transport: tuple[Mock, Mock]):
    session, _ = transport
    handler = JsonHttpHandler("https://example.test", session=session)

    class LegacyFormatter(JsonFormatter):
        def format(self, record):  # type: ignore[bad-override]
            return '{"legacy":"雪"}'

    for formatter, expected in [
        (logging.Formatter('{"message":"%(message)s"}'), '{"message":"hello"}'),
        (LegacyFormatter(), '{"legacy":"雪"}'),
    ]:
        handler.setFormatter(formatter)
        handler.handle(logging.makeLogRecord({"msg": "hello"}))
        assert session.request.call_args.kwargs["data"] == expected.encode("utf8")
    handler.close()
    return


@pytest.mark.parametrize(
    "failure", ["format", "request", "status", "cleanup", "status_and_cleanup"]
)
@pytest.mark.parametrize("raise_exceptions", [True, False])
def test_failures_do_not_escape_and_delivery_recovers(
    failure: str,
    raise_exceptions: bool,
    transport: tuple[Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    session, response = transport
    handler = JsonHttpHandler("https://example.test", session=session)
    error = ValueError(f"delivery failure: {failure}")
    if failure == "format":
        formatter = Mock(spec=logging.Formatter)
        formatter.format.side_effect = error
        handler.setFormatter(formatter)
    elif failure == "request":
        session.request.side_effect = error
    elif failure == "cleanup":
        response.close.side_effect = error
    else:
        response.raise_for_status.side_effect = error
        if failure == "status_and_cleanup":
            response.close.side_effect = RuntimeError("secondary cleanup failure")
    monkeypatch.setattr(logging, "raiseExceptions", raise_exceptions)
    logger = logging.Logger("http-test", logging.INFO)
    logger.addHandler(handler)
    logger.info("first")
    stderr = capsys.readouterr().err
    if raise_exceptions:
        assert str(error) in stderr
        assert "secondary cleanup failure" not in stderr
    else:
        assert stderr == ""
    if failure not in ("format", "request"):
        response.close.assert_called_once_with()

    handler.setFormatter(JsonFormatter())
    session.request.side_effect = None
    response.raise_for_status.side_effect = None
    response.close.side_effect = None
    logger.info("recovered")
    assert json.loads(session.request.call_args.kwargs["data"]) == {"message": "recovered"}
    assert capsys.readouterr().err == ""
    handler.close()
    return


@pytest.mark.parametrize("error", [ConnectionError("connection"), TimeoutError("timeout")])
def test_custom_error_hook_receives_active_exception(
    error: Exception, transport: tuple[Mock, Mock]
):
    session, _ = transport
    session.request.side_effect = error
    seen = []

    class RecordingHandler(JsonHttpHandler):
        def handleError(self, record: logging.LogRecord) -> None:
            seen.append((record, sys.exc_info()[1]))
            return

    handler = RecordingHandler("https://example.test", session=session)
    record = logging.makeLogRecord({"msg": "failure"})
    handler.handle(record)
    assert seen == [(record, error)]
    handler.close()
    return


def test_custom_error_hook_can_raise(transport: tuple[Mock, Mock]):
    session, _ = transport
    session.request.side_effect = TimeoutError()

    class RaisingHandler(JsonHttpHandler):
        def handleError(self, record: logging.LogRecord) -> None:
            raise RuntimeError("custom hook")

    handler = RaisingHandler("https://example.test", session=session)
    with pytest.raises(RuntimeError, match="custom hook"):
        handler.handle(logging.makeLogRecord({}))
    handler.close()
    return


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit()])
def test_process_control_exceptions_propagate(error: BaseException, transport: tuple[Mock, Mock]):
    session, _ = transport
    session.request.side_effect = error
    handler = JsonHttpHandler("https://example.test", session=session)
    with pytest.raises(type(error)):
        handler.handle(logging.makeLogRecord({}))
    handler.close()
    return


def test_missing_niquests_and_injected_session(
    monkeypatch: pytest.MonkeyPatch, transport: tuple[Mock, Mock]
):
    import pythonjsonlogger.utils

    real_find_spec = pythonjsonlogger.utils.importlib.util.find_spec
    monkeypatch.setattr(
        pythonjsonlogger.utils.importlib.util,
        "find_spec",
        lambda name: None if name == "niquests" else real_find_spec(name),
    )
    with pytest.raises(
        MissingPackageError, match="The 'niquests' package is required but could not be found"
    ):
        JsonHttpHandler("https://example.test")
    session, _ = transport
    handler = JsonHttpHandler("https://example.test", session=session)
    handler.handle(logging.makeLogRecord({"msg": "injected"}))
    session.request.assert_called_once()
    handler.close()
    return


def test_module_import_without_niquests():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['niquests'] = None; import pythonjsonlogger.http",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return


def test_default_session_ownership(monkeypatch: pytest.MonkeyPatch, transport: tuple[Mock, Mock]):
    session, _ = transport
    factory = Mock(return_value=session)
    availability = Mock(return_value=True)
    monkeypatch.setattr("pythonjsonlogger.http.package_is_available", availability)
    monkeypatch.setitem(sys.modules, "niquests", SimpleNamespace(Session=factory))
    handler = JsonHttpHandler("https://example.test")
    handler.handle(logging.makeLogRecord({"msg": "first"}))
    handler.handle(logging.makeLogRecord({"msg": "second"}))
    factory.assert_called_once_with()
    availability.assert_called_once_with("niquests", throw_error=True)
    handler.close()
    handler.close()
    session.close.assert_called_once_with()
    return


def test_dictconfig(transport: tuple[Mock, Mock]):
    session, _ = transport
    # Use a standalone configurator so unrelated application loggers stay untouched.
    config = logging.config.DictConfigurator(
        {
            "version": 1,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.json.JsonFormatter",
                    "fmt": "message,levelname",
                    "style": ",",
                }
            },
        }
    )
    config.config["formatters"]["json"] = config.configure_formatter(
        config.config["formatters"]["json"]
    )
    handler = config.configure_handler(
        {
            "class": "pythonjsonlogger.http.JsonHttpHandler",
            "url": "https://example.test",
            "session": session,
            "method": "PUT",
            "level": "WARNING",
            "formatter": "json",
        }
    )
    assert handler.level == logging.WARNING
    handler.handle(logging.makeLogRecord({"msg": "configured", "levelname": "WARNING"}))
    assert session.request.call_args.args[0] == "PUT"
    assert json.loads(session.request.call_args.kwargs["data"]) == {
        "message": "configured",
        "levelname": "WARNING",
    }
    handler.close()
    return


@pytest.fixture
def receiver() -> Generator[tuple[str, Queue[tuple[str, bytes, str | None]]]]:
    received: Queue[tuple[str, bytes, str | None]] = Queue()

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"]))
            received.put((self.command, data, self.headers.get("Content-Type")))
            self.send_response(500 if self.path == "/fail" else 200)
            self.end_headers()
            return

        do_PUT = do_POST

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return


@pytest.mark.parametrize("client", ["requests", "niquests"])
@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_real_client_delivery(client: str, method: str, receiver, monkeypatch: pytest.MonkeyPatch):
    module = pytest.importorskip(client)
    url, received = receiver
    with module.Session() as session:
        session.trust_env = False
        handler = JsonHttpHandler(url + "/logs", method=method, session=session)
        handler.setFormatter(JsonFormatter(json_ensure_ascii=False))
        handler.handle(logging.makeLogRecord({"msg": "雪"}))
        assert received.get(timeout=5) == (
            method,
            '{"message": "雪"}'.encode("utf8"),
            "application/json",
        )
        errors: list[Any] = []
        monkeypatch.setattr(handler, "handleError", lambda record: errors.append(sys.exc_info()[1]))
        handler.url = url + "/fail"
        handler.handle(logging.makeLogRecord({"msg": "rejected"}))
        assert len(errors) == 1
        assert "500" in str(errors[0])
        handler.close()
    return


@pytest.mark.parametrize("stage", ["status", "cleanup"])
def test_process_control_in_response_is_not_swallowed(stage: str, transport: tuple[Mock, Mock]):
    session, response = transport
    if stage == "status":
        response.raise_for_status.side_effect = KeyboardInterrupt()
    else:
        response.close.side_effect = KeyboardInterrupt()
    handler = JsonHttpHandler("https://example.test", session=session)
    with pytest.raises(KeyboardInterrupt):
        handler.handle(logging.makeLogRecord({}))
    response.close.assert_called_once_with()
    handler.close()
    return


def test_session_close_failure_is_not_repeated(
    monkeypatch: pytest.MonkeyPatch, transport: tuple[Mock, Mock]
):
    session, _ = transport
    monkeypatch.setattr("pythonjsonlogger.http.package_is_available", lambda *args, **kwargs: True)
    monkeypatch.setitem(sys.modules, "niquests", SimpleNamespace(Session=lambda: session))
    session.close.side_effect = RuntimeError("close failure")
    handler = JsonHttpHandler("https://example.test")
    with pytest.raises(RuntimeError, match="close failure"):
        handler.close()
    handler.close()
    session.close.assert_called_once_with()
    return


def test_invalid_prefix_follows_emission_error_path(transport: tuple[Mock, Mock]):
    session, _ = transport
    handler = JsonHttpHandler("https://example.test", session=session)
    formatter = JsonFormatter()
    formatter.prefix = 0  # type: ignore[bad-assignment]
    handler.setFormatter(formatter)
    seen: list[BaseException | None] = []
    handler.handleError = lambda record: seen.append(sys.exc_info()[1])
    handler.handle(logging.makeLogRecord({"msg": "invalid prefix"}))
    assert len(seen) == 1
    assert isinstance(seen[0], (AttributeError, TypeError))
    session.request.assert_not_called()
    handler.close()
    return
