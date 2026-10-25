# Send JSON logs over HTTP

[`JsonHttpHandler`][pythonjsonlogger.http.JsonHttpHandler] sends each formatted log record as the body of a synchronous HTTP request. It supports `POST` and `PUT` through Requests-compatible sessions.

*New in 4.3.0*

## Configure a receiver and formatter

Your receiver must accept one JSON document per request at the configured URL. Configure authentication, required fields, and any destination-specific payload structure to match its ingestion API.

The formatter must produce valid JSON. Use `prefix=""`, which is the default for the built-in JSON formatters. A textual prefix generally makes the payload invalid JSON. `prefix=0` is not a valid formatter configuration: the prefix must be a string. The handler transmits formatter output unchanged and does not validate JSON, remove prefixes, or add a newline. Custom serializers and formatters are responsible for their output's validity.

The handler defaults to `JsonFormatter()`. Use `setFormatter()` to configure fields or select `OrjsonFormatter` or `MsgspecFormatter`. Standard logging formatters also work if their output is valid JSON; interpolating a message into a JSON-looking format string does not reliably escape it.

## Use the default Niquests session

Install Niquests separately:

```shell
pip install python-json-logger niquests
```

```python
import logging

from pythonjsonlogger.http import JsonHttpHandler
from pythonjsonlogger.json import JsonFormatter

handler = JsonHttpHandler("https://logs.example.com/ingest")
handler.setFormatter(JsonFormatter("message,levelname,name", style=","))

logger = logging.getLogger("application")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
try:
    logger.info("Application started", extra={"service": "example"})
finally:
    logger.removeHandler(handler)
    handler.close()
```

Replace the URL with your receiver's ingestion endpoint. Without a supplied session, the handler creates and reuses a Niquests session and closes it when the handler closes. If Niquests is unavailable, construction raises `MissingPackageError`. Importing `pythonjsonlogger.http` does not require Niquests.

Requests default to `POST`, `Content-Type: application/json`, and a five-second timeout. Set `method="PUT"` to use `PUT`. `request_kwargs` accepts options supported by your session, including authentication, headers, and timeout. An explicit content type, in any letter case, overrides the default. An explicit timeout, including `None`, overrides the handler's default; the session determines its meaning. Timeout behavior is client-specific and does not necessarily impose an overall five-second delivery deadline.

The handler copies the options mapping and headers when constructed. The `data`, `json`, `files`, `method`, and `url` options are reserved and raise `ValueError` if passed in `request_kwargs`.

## Supply a session

You can supply a [Requests session](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects) or a [Niquests session](https://niquests.readthedocs.io/en/latest/api.html#session). Install your chosen client separately. Supplied sessions do not require Niquests, and you retain responsibility for closing them.

```python
import logging

import requests

from pythonjsonlogger.http import JsonHttpHandler

with requests.Session() as session:
    handler = JsonHttpHandler(
        "https://logs.example.com/ingest",
        method="PUT",
        session=session,
        request_kwargs={
            "headers": {"Authorization": "Bearer REPLACE_WITH_TOKEN"},
            "timeout": 10,
        },
    )
    logger = logging.getLogger("application")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("Application started")
    finally:
        logger.removeHandler(handler)
        handler.close()
```

Replace `REPLACE_WITH_TOKEN` with your receiver's token and use its required authentication scheme. Close the handler before closing a supplied session. Session options and credentials follow the selected client's rules.

Compatible sessions provide synchronous `request(method, url, data=payload, **kwargs)` calls. Responses must provide synchronous `raise_for_status()` and `close()` methods. The payload is UTF-8 bytes. HTTPX clients and asynchronous clients, including aiohttp, are not supported by this interface.

## Configure logging with a dictionary

```python
import logging
import logging.config

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "fmt": "message,levelname,name",
                "style": ",",
            },
        },
        "handlers": {
            "http": {
                "class": "pythonjsonlogger.http.JsonHttpHandler",
                "url": "https://logs.example.com/ingest",
                "method": "POST",
                "formatter": "json",
                "level": "INFO",
                "request_kwargs": {"timeout": 10},
            },
        },
        "loggers": {
            "application": {
                "handlers": ["http"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
)
logging.getLogger("application").info("Application started")
```

This example requires Niquests. To inject an existing session programmatically, include it as the handler's `session` value.

## Handle delivery failures

Formatting errors, connection failures, timeouts, unsuccessful HTTP status checks, and response-cleanup errors call `handleError(record)`. The handler calls the response's `raise_for_status()` method; the selected client's status rules apply. Response cleanup preserves an original delivery error if cleanup also fails.

With the standard `handleError()` implementation, ordinary emission errors do not propagate to your application:

- When `logging.raiseExceptions` is `True` (the Python default), logging writes diagnostics to stderr. This flag does not make the handler re-raise the delivery error.
- When `logging.raiseExceptions` is `False`, logging silently ignores the error. This setting affects logging globally.

Failed records are dropped. The handler does not retry, batch, persist records, or report failures by logging another record. A session may apply its own retry policy. Constructor errors, such as an unsupported method or missing Niquests, still raise immediately. Filter errors, explicitly closing a session, and exceptions raised by custom error hooks are outside the emission error guarantee. Process-control exceptions such as `KeyboardInterrupt` and `SystemExit` propagate.

Override `handleError()` to count failures or report them through a separate channel. The hook runs with the delivery exception active and can inspect `sys.exc_info()`. An override that raises can cause the application logging call to raise. Avoid logging through the same handler from the hook, a session hook, or the HTTP client's internal logger, since that can recursively send requests. Configure the handler on an application logger, as in these examples, rather than routing its HTTP client's diagnostics back to it.

## Move delivery to a worker thread

HTTP delivery blocks the thread that calls the handler. Use [`QueueHandler` and `QueueListener`](https://docs.python.org/3/library/logging.handlers.html#queuehandler) when application threads should enqueue records instead:

```python
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

from pythonjsonlogger.http import JsonHttpHandler

queue = Queue()
http_handler = JsonHttpHandler("https://logs.example.com/ingest")
queue_handler = QueueHandler(queue)
listener = QueueListener(queue, http_handler)
logger = logging.getLogger("application")
logger.setLevel(logging.INFO)
logger.addHandler(queue_handler)
listener.start()
try:
    logger.info("Application started")
finally:
    logger.removeHandler(queue_handler)
    listener.stop()
    http_handler.close()
```

Stop the listener before closing the HTTP handler so queued records can finish delivery. This example uses an unbounded in-memory queue; choose a queue capacity and overflow policy appropriate for your application. Standard `QueueHandler` preparation can alter message and exception fields before the JSON formatter receives them.

## Internal byte output

The handler uses the private, non-stable `format(record, _output_type="bytes")` interface on built-in JSON formatters. Normal `format(record)` calls still return strings. Orjson and msgspec can send their native bytes without decoding and re-encoding them. Existing string serialization overrides remain effective through a UTF-8 fallback. A subclass that overrides `format(record)` uses its normal string output.
