# Logging Time

Python JSON Logger supports two ways to include the time a log record was created:

| Option | How to enable it | Default representation |
| --- | --- | --- |
| `timestamp` | Pass `timestamp=True` to the formatter | A UTC datetime serialized by the JSON encoder |
| `asctime` | Include `%(asctime)s` in the format | A local-time string formatted by Python's `logging.Formatter` |

Neither is included by default. Both use the record's creation time, not the time at which a handler formats it.

## UTC timestamps

Use `timestamp=True` for a UTC timestamp without customizing the standard library's time formatter. With `pythonjsonlogger.json.JsonFormatter` and its default encoder, the result is an ISO 8601 string, **not** a Unix epoch number. Fractional seconds are included when nonzero.

The examples below use a record with a fixed creation time so that the output is reproducible. In an application, attach the formatter to a handler as shown in the [quick start](quickstart.md).

```python
import logging

from pythonjsonlogger.json import JsonFormatter

record = logging.makeLogRecord(
    {"msg": "Hello", "args": (), "created": 1500000000.125, "msecs": 125.0}
)
formatter = JsonFormatter(timestamp=True)
print(formatter.format(record))
```

```json
{"message": "Hello", "timestamp": "2017-07-14T02:40:00.125000+00:00"}
```

Pass a nonempty string to choose a different output field name:

```python
formatter = JsonFormatter(timestamp="time")
print(formatter.format(record))
```

```json
{"message": "Hello", "time": "2017-07-14T02:40:00.125000+00:00"}
```

The field does not need to appear in `fmt`. Conversely, including `%(timestamp)s` in `fmt` does **not** enable timestamp generation. Without `timestamp=True` or a value supplied on the record, it produces `null`:

```python
formatter = JsonFormatter("%(message)s %(timestamp)s")
print(formatter.format(record))
```

```json
{"message": "Hello", "timestamp": null}
```

The formatter adds an aware UTC `datetime` to the data before JSON serialization. Other encoders or a custom encoder may represent that datetime differently. Neither `datefmt` nor `converter` changes this value.

## Standard-library time formatting with `asctime`

Use `asctime` when you need the standard library's `datefmt` or `converter` behavior. By default, `logging.Formatter` uses local time and a format such as `2017-07-14 02:40:00,125`.

Set `converter` to `time.gmtime` for UTC. The following example reuses the record above and sets UTC explicitly so that its output does not depend on the machine's local time zone:

```python
import time

formatter = JsonFormatter("%(message)s %(asctime)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
formatter.converter = time.gmtime
print(formatter.format(record))
```

```json
{"message": "Hello", "asctime": "2017-07-14T02:40:00Z"}
```

`datefmt` uses [`time.strftime`](https://docs.python.org/3/library/time.html#time.strftime), not `datetime.strftime`. In particular, `%f` is not supported for formatting fractional seconds here. A supplied `datefmt` replaces the default time format, including its automatic millisecond suffix. For further customization, override [`logging.Formatter.formatTime`](https://docs.python.org/3/library/logging.html#logging.Formatter.formatTime).

Renaming `asctime` with `rename_fields={"asctime": "timestamp"}` only changes its field name; it does not turn the formatted string into a UTC datetime. You can enable both `asctime` and `timestamp`, but give them distinct output names: a generated timestamp overwrites an earlier value using the same output key, including a renamed `asctime` field.

## Configure timestamps with `dictConfig`

No custom formatter subclass is needed to enable `timestamp` through [`logging.config.dictConfig`](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig). Pass it as a formatter option alongside `format`:

```python
import logging.config

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(levelname)s %(message)s",
                "timestamp": True,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            }
        },
        "loggers": {
            "example": {"handlers": ["console"], "level": "INFO", "propagate": False}
        },
    }
)
logging.getLogger("example").info("Hello")
```

This emits `levelname`, `message`, and `timestamp`; the timestamp reflects the actual log record's creation time. Use `"timestamp": "time"` instead to select a different key. In a YAML configuration loaded for `dictConfig`, use `timestamp: true` (a boolean), not `timestamp: "true"` (which selects the field name `"true"`).
