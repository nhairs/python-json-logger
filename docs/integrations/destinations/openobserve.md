# OpenObserve

OpenObserve can ingest arbitrary application JSON through supported forwarders or HTTP APIs. This recipe uses the JSON ingestion API's `_timestamp` convention so application event time can be preserved.

## Format the event

```python
import logging

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter(
    "%(message)s %(levelname)s %(name)s",
    rename_fields={"levelname": "level", "name": "logger"},
    static_fields={"service": "billing", "environment": "dev"},
    timestamp="_timestamp",
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
{"message": "Payment accepted", "level": "INFO", "logger": "billing", "service": "billing", "environment": "dev", "_timestamp": "2017-07-14T02:40:00.125000+00:00"}
```

The [JSON ingestion reference](https://openobserve.ai/docs/reference/api/ingestion/logs/json/) accepts ISO 8601 timestamp strings and microsecond Unix timestamps. This formatter emits a UTC string. If no timestamp is supplied, the service assigns the current time. `message`, `level`, `logger`, `service`, and `environment` are application conventions here, not required API fields. Exceptions use `exc_info`, and additional context can be passed through `extra`.

## Delivery options

| Method | When to choose it | Receiving setup |
| --- | --- | --- |
| [stdout/stderr](../delivery/streams.md) | A container or supervisor collects logs | A forwarder unwraps runtime envelopes, parses the application JSON, and sends records to OpenObserve |
| [Files](../delivery/files.md) | An agent can read local JSON files | A forwarder tails and parses one object per line, then sends records to the selected stream |
| [HTTP sender](../delivery/handlers.md) | A client already implements API delivery | Authenticated JSON batch or multi-line API with matching framing |

Attach the formatter to the stream or file handler. Configure collection through OpenObserve's [Fluent Bit](https://openobserve.ai/docs/ingestion/logs/fluent-bit/) or [Vector](https://openobserve.ai/docs/ingestion/logs/vector/) instructions. Supply the destination organization, stream, endpoint, and authentication in the forwarder.

Check that the forwarder preserves application `_timestamp` instead of replacing it with collection time. Parse runtime envelopes and the inner JSON before shipping; otherwise fields may arrive inside an unparsed `log` or `message` string.

The `_json` endpoint expects a JSON array of events, rather than a single JSON object or a raw file of JSON lines. The [_multi endpoint](https://openobserve.ai/docs/reference/api/ingestion/logs/multi/) accepts newline-delimited events. Choose the framing for the actual endpoint and follow the [HTTP handler compatibility notes](../delivery/handlers.md). Use current timestamps in ingestion checks; the historical record above demonstrates formatter output only.
