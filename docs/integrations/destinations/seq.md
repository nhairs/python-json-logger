# Seq

Seq accepts Compact Log Event Format (CLEF). This recipe uses rendered messages, normalizes Python's standard severity names, and retains ordinary application properties.

## Format CLEF events

```python
import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter


class ClefFormatter(JsonFormatter):
    """Adapt Python's standard level names to Seq conventions."""

    def process_log_record(self, log_data: dict[str, Any]) -> dict[str, Any]:
        levels = {
            "DEBUG": "Debug",
            "INFO": "Information",
            "WARNING": "Warning",
            "ERROR": "Error",
            "CRITICAL": "Fatal",
        }
        level = log_data.get("@l")
        if isinstance(level, str):
            log_data["@l"] = levels.get(level, level)
        return log_data


formatter = ClefFormatter(
    "%(message)s %(levelname)s %(name)s",
    rename_fields={
        "message": "@m",
        "levelname": "@l",
        "name": "logger",
        "exc_info": "@x",
    },
    static_fields={"service": "billing", "environment": "dev"},
    timestamp="@t",
)
record = logging.makeLogRecord(
    {
        "name": "billing",
        "msg": "Payment accepted",
        "args": (),
        "levelname": "INFO",
        "levelno": logging.INFO,
        "created": 1500000000.125,
    }
)
print(formatter.format(record))
```

```json
{"@m": "Payment accepted", "@l": "Information", "logger": "billing", "service": "billing", "environment": "dev", "@t": "2017-07-14T02:40:00.125000+00:00"}
```

Attach this formatter to a shared stream or file recipe. Normal logging calls supply the current timestamp; no manual record construction is needed. Standard exception formatting yields an `@x` string when an exception is logged. Keep `exc_info_as_array` disabled for this recipe. Custom level names pass through unchanged; define a mapping for them if you need standard Seq severity behavior.

The [CLEF reference](https://datalust.co/docs/posting-raw-events) defines `@t` as required and `@m` as rendered text. Python's `%` message interpolation has already happened, so this example does not preserve a message template in `@mt`. Leave the reserved `@` namespace to CLEF. For an application property beginning with `@`, use its doubled form, such as `@@customer`, in the output; this formatter does not automatically escape arbitrary property names.

## Delivery options

| Method | When to choose it | Receiving setup |
| --- | --- | --- |
| [Files](../delivery/files.md) | Local retention or later import is useful | `seqcli ingest` reads newline-delimited CLEF from the file and sends it to Seq |
| [stdout](../delivery/streams.md) | A pipeline can run alongside the application | `seqcli ingest` reads CLEF from stdin; keep other output off stdout |
| [HTTP sender](../delivery/handlers.md) | A client already handles batching and failures | CLEF ingestion endpoint with matching content type and authentication |

Install and configure the [Seq command-line client](https://datalust.co/docs/command-line-client) with your server URL and an ingestion API key. Follow the [file import instructions](https://datalust.co/docs/importing-log-files) for `seqcli ingest --json` with an input file, or omit the input file to read stdin. Use the destination formatter above instead of the generic formatter in the shared delivery recipe. Avoid repeatedly importing the same file unless you intend to duplicate its events.

For direct HTTP delivery, follow [Seq's ingestion instructions](https://datalust.co/docs/posting-raw-events) for newline-delimited CLEF sent to `/ingest/clef`, its content type, and API-key handling. Ordinary `HTTPHandler` does not send that payload; see [handler compatibility](../delivery/handlers.md).
