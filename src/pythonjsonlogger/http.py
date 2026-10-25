"""Send formatted JSON using synchronous Requests-compatible HTTP sessions."""

### IMPORTS
### ============================================================================
from __future__ import annotations

from collections.abc import Mapping
import importlib
import logging
from typing import Any

from .core import BaseJsonFormatter
from .json import JsonFormatter
from .utils import package_is_available


### CLASSES
### ============================================================================
class JsonHttpHandler(logging.Handler):
    """Send one JSON log record per HTTP request.

    Sessions must provide synchronous `request(method, url, data=..., **kwargs)`
    and responses with `raise_for_status()` and `close()` methods. Requests and
    Niquests sessions support this interface. HTTPX and async clients are not supported.

    The formatter must produce valid JSON, normally with `prefix=""`. Output is
    transmitted unchanged, without JSON validation. Delivery is synchronous; use
    `logging.handlers.QueueHandler` and `QueueListener` to move it to another thread.

    *New in 4.3.0*
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = "POST",
        session: Any = None,
        level: int | str = logging.NOTSET,
        request_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize the handler.

        Args:
            url: Receiver URL.
            method: POST or PUT (case insensitive).
            session: Requests-compatible session. If omitted, create a Niquests
                session and close it when the handler closes. Supplied sessions
                remain owned by the caller and are not closed by this handler.
            level: Logging threshold.
            request_kwargs: Additional session request options, such as headers,
                authentication, or timeout. Defaults to a five-second timeout and
                `Content-Type: application/json`, unless explicitly supplied.
                Options must be supported by the chosen session implementation.

        Raises:
            ValueError: Method is unsupported or request options conflict with
                the handler's method, URL, or body.
            pythonjsonlogger.exception.MissingPackageError: No session was
                supplied and Niquests is not installed.
        """
        method = method.upper()
        if method not in ("POST", "PUT"):
            raise ValueError("method must be POST or PUT")
        kwargs = dict(request_kwargs) if request_kwargs is not None else {}
        conflicts = {"data", "json", "files", "method", "url"}.intersection(kwargs)
        if conflicts:
            raise ValueError(f"Conflicting request options: {', '.join(sorted(conflicts))}")
        headers = dict(kwargs.get("headers") or {})
        if not any(key.lower() == "content-type" for key in headers):
            headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers
        kwargs.setdefault("timeout", 5)

        super().__init__(level)
        self.url = url
        self.method = method
        self.session = session
        self.request_kwargs = kwargs
        self._owns_session = False
        self._transport_closed = False
        self.setFormatter(JsonFormatter())
        if session is None:
            package_is_available("niquests", throw_error=True)
            self.session = importlib.import_module("niquests").Session()
            self._owns_session = True
        return

    def emit(self, record: logging.LogRecord) -> None:
        """Send a record, routing formatting and delivery failures to `handleError`.

        Failed records are dropped without retries. The standard error hook writes
        diagnostics to stderr if `logging.raiseExceptions` is true, otherwise it
        ignores failures. A custom `handleError` override may raise exceptions.
        """
        if self._transport_closed:
            return
        try:
            formatter = self.formatter
            # An existing format() override may not accept the private keyword.
            if (
                isinstance(formatter, BaseJsonFormatter)
                and getattr(formatter.format, "__func__", None) is BaseJsonFormatter.format
            ):
                payload = formatter.format(record, _output_type="bytes")
            else:
                payload = self.format(record).encode("utf8")
            response = self.session.request(
                self.method, self.url, data=payload, **self.request_kwargs
            )
            try:
                response.raise_for_status()
            except BaseException:
                # Cleanup must not replace the delivery error reported to handleError.
                try:
                    response.close()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
                raise
            response.close()
        except Exception:  # pylint: disable=broad-exception-caught
            self.handleError(record)
        return

    def close(self) -> None:
        """Close an owned session once, leaving supplied sessions open."""
        self.acquire()
        try:
            if not self._transport_closed:
                self._transport_closed = True
                try:
                    if self._owns_session:
                        self.session.close()
                finally:
                    super().close()
        finally:
            self.release()
        return
