# Write to stdout or stderr

Use streams when a container runtime, process supervisor, or pipeline already collects application output. Choose stdout when it is dedicated to logs; choose stderr when stdout carries the application's results. Without an explicit stream, `StreamHandler` uses stderr.

```python
import logging
import sys

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter("%(message)s %(levelname)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger("stream-example")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(handler)
logger.info("Ready")
```

stdout:

```json
{"message": "Ready", "levelname": "INFO"}
```

Replace `formatter` with the formatter from your destination page. Change the stream to `sys.stderr` if required. Configure handlers once during application startup; repeatedly adding handlers emits duplicates. Here `propagate=False` prevents an ancestor logger from writing the same event again.

## Split events by severity

If your infrastructure expects errors on stderr, use both a minimum level on the stderr handler and an upper-bound filter on stdout. Setting stdout to INFO and stderr to ERROR without the filter duplicates errors.

```python
import logging
import sys

from pythonjsonlogger.json import JsonFormatter


class BelowError(logging.Filter):
    """Keep events below ERROR on stdout."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.ERROR


formatter = JsonFormatter("%(message)s %(levelname)s")
stdout = logging.StreamHandler(sys.stdout)
stdout.setLevel(logging.DEBUG)
stdout.addFilter(BelowError())
stdout.setFormatter(formatter)

stderr = logging.StreamHandler(sys.stderr)
stderr.setLevel(logging.ERROR)
stderr.setFormatter(formatter)

logger = logging.getLogger("split-example")
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(stdout)
logger.addHandler(stderr)
logger.debug("Debug detail")
logger.info("Ready")
logger.warning("Retrying")
logger.error("Failed")
logger.critical("Stopping")
```

stdout contains the DEBUG, INFO, and WARNING events; stderr contains ERROR and CRITICAL. Every event appears once. Stream choice does not replace the structured severity field. A collector may assign its own stream-based severity unless configured to use the payload.

## Collect the output

Keep the formatter's default compact JSON and the handler's newline terminator. Embedded newlines, including traceback lines, are escaped inside JSON strings; do not enable pretty printing or add non-JSON prefixes to these streams. Keep other output off a stream that a downstream client expects to contain only JSON.

A runtime may wrap your line in its own JSON or CRI envelope. The collector must decode that envelope and then parse the application JSON. Writing to stdout does not ship logs by itself, and stream collection does not guarantee delivery during process or collector failures.

Destination-specific setup and receiving requirements:

- [Loki / Grafana Cloud](../destinations/loki.md#delivery-options): collect runtime logs with Alloy.
- [OpenObserve](../destinations/openobserve.md#delivery-options): collect runtime logs with a supported forwarder.
- [Seq](../destinations/seq.md#delivery-options): pipe CLEF output to `seqcli`.
- [Graylog](../destinations/graylog.md#delivery-options): use a forwarder that targets an appropriate input.
