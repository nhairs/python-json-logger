# Choose output fields

Required fields are those provided by `fmt`. Use the destination's conventions to decide which record attributes to select, rename, or transform. A field required by your formatter is not necessarily required by the destination's ingestion API.

This standalone example formats a fixed record so the output is reproducible:

```python
import logging

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter(
    "%(message)s %(levelname)s %(name)s",
    rename_fields={"levelname": "level", "name": "logger"},
    static_fields={"service": "billing", "environment": "dev"},
    timestamp=True,
)
record = logging.makeLogRecord(
    {
        "name": "billing",
        "msg": "Payment accepted",
        "args": (),
        "levelname": "INFO",
        "levelno": logging.INFO,
        "created": 1500000000.125,
        "request_id": "request-123",
    }
)
print(formatter.format(record))
```

```json
{"message": "Payment accepted", "level": "INFO", "logger": "billing", "service": "billing", "environment": "dev", "request_id": "request-123", "timestamp": "2017-07-14T02:40:00.125000+00:00"}
```

In an application, attach `formatter` to a handler from the [delivery recipes](index.md#choose-a-delivery-route). You do not need to construct records manually. Each destination page uses the same fixed-record approach to demonstrate its output independently of a handler.

`timestamp=True` generates event time from the record's creation time. It need not be selected in `fmt`. Pass a string, such as `timestamp="_timestamp"`, to choose its output name. See [Logging Time](../time.md) for time representations and the difference between `timestamp` and `asctime`.

`static_fields` supplies service and environment context, but message fields and `extra` can override it. See the quickstart's [field precedence](../quickstart.md#field-precedence). Request and trace identifiers must come from your application or instrumentation; a formatter does not generate tracing context. See [request and trace IDs](../cookbook.md#request-trace-ids).

## Compare destination conventions

These are the conventions used by the recipes. Except for the Seq CLEF requirements noted below, they describe the chosen ingestion configuration rather than a universal required schema.

| Meaning | Loki JSON payload | Graylog syslog JSON payload | OpenObserve JSON event | Seq CLEF event |
| --- | --- | --- | --- | --- |
| Event time | `timestamp`, UTC ISO 8601; collector must parse it | `app_timestamp`, UTC ISO 8601; distinct from syslog header | `_timestamp`, UTC ISO 8601 accepted by JSON ingestion | `@t`, required ISO 8601 timestamp |
| Message | `message` | `app_message`; retain native `message` | `message` | `@m`, rendered text in this recipe |
| Severity | `level`, text | `app_level`, text; native `level` comes from syslog priority | `level`, text | `@l`, normalized text; optional, defaults to informational |
| Logger | `logger` | `app_logger` | `logger` | `logger` |
| Service/environment | `service`, `environment`; explicitly map low-cardinality labels | `app_service`, `app_environment` | `service`, `environment` | `service`, `environment` |
| Exception | `exc_info` string | `app_exception` string | `exc_info` string | `@x`, optional string |
| Request/trace context | Application fields; not indexed labels | Prefixed application fields | Application fields | Ordinary properties; use native trace fields only with valid context |

Each [destination page](index.md#choose-a-delivery-route) links to the authoritative schema or ingestion reference and explains what is recognized automatically. Field names alone do not make a destination use your event timestamp or service metadata.

## Transform values explicitly

`rename_fields={"levelname": "level"}` changes the key but retains a value such as `"WARNING"`. It does not convert that value into a syslog severity number or an OpenTelemetry severity number. Similarly, renaming to `"log.level"` creates a literal dotted key, not a nested `log` object.

Use a collector transformation or override `process_log_record` when you need value conversion or nesting. The [Seq recipe](destinations/seq.md) demonstrates severity normalization. Avoid collisions between required fields, renamed fields, and application properties. Preserve destination-reserved fields for their defined meanings.
