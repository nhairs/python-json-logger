# Cookbook

Recipies for common tasks.

## Include all fields

By default Python JSON Logger will not include fields [defined in the standard library](https://docs.python.org/3/library/logging.html#logrecord-attributes) unless they are included in the format. Manually including all these fields is tedious and Python version specific. Instead of adding them as explicit fields, we can add them implicitly be ensuring they are not in the `reserver_attrs` argument of the formatter.

```python
all_fields_formatter = JsonFormatter(reserved_attrs=[])
```

## Custom Styles

It is possible to support custom `style`s by setting `validate=False` and overriding the `parse` method.

For example:

```python
class CommaSupport(JsonFormatter):
    def parse(self) -> list[str]:
        if isinstance(self._style, str) and self._style == ",":
            return self._fmt.split(",")
        return super().parse()

formatter = CommaSupport("message,asctime", style=",", validate=False)
```

## Modifying the logged data

You can modify the `dict` of data that will be logged by overriding the `process_log_record` method to modify fields before they are serialized to JSON.

```python
class SillyFormatter(JsonFormatter):
    def process_log_record(self, log_data):
        new_record = {k[::-1]: v for k, v in log_data.items()}
        return new_record
```


## Terminal colors

For local development, a custom formatter can wrap each JSON line in an ANSI color
chosen by the record's log level. Apply the color **after** `JsonFormatter.format`
serializes the record. Adding escape sequences to `levelname` or other fields in
`process_log_record` instead puts JSON-escaped strings into the payload, not terminal
formatting around it.

The following standalone example is intended for ANSI-capable terminals. It enables
color when standard error is a terminal, with plain output when redirected or when
`NO_COLOR` is set to a non-empty value. `isatty()` does not detect ANSI support.
Configure these handlers once at application startup.

```python title="terminal_color.py"
import logging
import os
import sys

from pythonjsonlogger.json import JsonFormatter


class TerminalColorFormatter(JsonFormatter):
    """Wrap serialized JSON in terminal colors without coloring record fields."""

    COLORS = {
        logging.DEBUG: "\x1b[36m",
        logging.INFO: "\x1b[32m",
        logging.WARNING: "\x1b[33m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[1;31m",
    }

    def __init__(self, fmt: str, *, use_color: bool = False) -> None:
        """Enable color only when the destination supports ANSI escapes."""
        super().__init__(fmt)
        self.use_color = use_color
        return

    def format(self, record: logging.LogRecord) -> str:
        """Format normally, then color known levels when enabled."""
        formatted = super().format(record)
        color = self.COLORS.get(record.levelno, "") if self.use_color else ""
        if color:
            return f"{color}{formatted}\x1b[0m"
        return formatted


fmt = "%(levelname)s %(message)s"
console = logging.StreamHandler(sys.stderr)
console.setFormatter(
    TerminalColorFormatter(fmt, use_color=sys.stderr.isatty() and not os.environ.get("NO_COLOR"))
)

# Keep a separate, uncolored destination for log ingestion.
machine = logging.StreamHandler(sys.stdout)
machine.setFormatter(JsonFormatter(fmt))

logger = logging.getLogger("terminal-color-example")
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(console)
logger.addHandler(machine)
logger.warning("Hello %s", "world", extra={"request_id": "abc"})
```

The machine handler emits the following JSON, while the console handler wraps the
same line in yellow when color is enabled:

```json
{"levelname": "WARNING", "message": "Hello world", "request_id": "abc"}
```

This recipe colors the whole line, not just the `levelname` value. Unknown/custom
levels remain uncolored unless added to `COLORS`. Set `use_color=False` to disable
color explicitly, including on terminals without ANSI support. The terminal check
is made when configuring the handler; recalculate it if you change its stream.

!!! warning
    Colored console output is **not raw JSON**. Send the machine handler's output
    to your log collector instead, and do not merge the colored standard error
    stream into it. The wrapper leaves serialization to `JsonFormatter`, so message
    interpolation, dictionary messages, extra fields and exception escaping still
    work normally. It does not add color to the shared `LogRecord` or caller's data.

## Request / Trace IDs

There are many ways to add consistent request IDs to your logging. The exact method will depend on your needs and application.

```python
## Common Setup
## -----------------------------------------------------------------------------
import logging
import uuid
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger("test")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)
```

One method would be to inject the request ID into each log call using the `extra` argument.
```python
## Solution 1
## -----------------------------------------------------------------------------
formatter = JsonFormatter()
handler.setFormatter(formatter)

def main_1():
    print("========== MAIN 1 ==========")
    for i in range(3):
        request_id = uuid.uuid4()
        logger.info("loop start", extra={"request_id": request_id})
        logger.info(f"loop {i}", extra={"request_id": request_id})
        logger.info("loop end", extra={"request_id": request_id})
    return

main_1()
```

Another method would be to use a filter to modify the `LogRecord` attributes. This would also allow us to use it in any other standard logging machinery. For this example I've manually set a `REQUEST_ID` global and some helper functions, but you might already have stuff available to you; for example, if you're using a web-framework with baked in request IDs.

This is based on the [logging cookbook filter recipie](https://docs.python.org/3/howto/logging-cookbook.html#using-filters-to-impart-contextual-information).

```python
## Solution 2
## -----------------------------------------------------------------------------
REQUEST_ID: str | None = None

def get_request_id() -> str:
    return REQUEST_ID

def generate_request_id():
    global REQUEST_ID
    REQUEST_ID = str(uuid.uuid4())

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() # Add request_id to the LogRecord
        return True

request_id_filter = RequestIdFilter()
logger.addFilter(request_id_filter)

def main_2():
    print("========== MAIN 2 ==========")
    for i in range(3):
        generate_request_id()
        logger.info("loop start")
        logger.info(f"loop {i}")
        logger.info("loop end")
    return

main_2()

logger.removeFilter(request_id_filter)
```

Another method would be to create a custom formatter class and override the `process_log_record` method. This allows us to inject fields into the record before we log it without modifying the original `LogRecord`.

```python
## Solution 3
## -----------------------------------------------------------------------------
# Reuse REQUEST_ID stuff from solution 2
class MyFormatter(JsonFormatter):
    def process_log_record(self, log_data):
        log_data["request_id"] = get_request_id()
        return log_data

handler.setFormatter(MyFormatter())

def main_3():
    print("========== MAIN 3 ==========")
    for i in range(3):
        generate_request_id()
        logger.info("loop start")
        logger.info(f"loop {i}")
        logger.info("loop end")
    return

main_3()
```

## Using `fileConfig`

To use the module with a yaml config file using the [`fileConfig` function](https://docs.python.org/3/library/logging.config.html#logging.config.fileConfig), use the class `pythonjsonlogger.json.JsonFormatter`. Here is a sample config file:

```yaml title="example_config.yaml"
version: 1
disable_existing_loggers: False
formatters:
  default:
    "()": pythonjsonlogger.json.JsonFormatter
    format: "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)s %(message)s"
    json_default: ext://logging_config.my_json_default
    rename_fields:
      "asctime": "timestamp"
      "levelname": "status"
    static_fields:
      "service": ext://logging_config.PROJECT_NAME
      "env": ext://logging_config.ENVIRONMENT
      "version": ext://logging_config.PROJECT_VERSION
      "app_log": "true"
handlers:
  default:
    formatter: default
    class: logging.StreamHandler
    stream: ext://sys.stderr
  access:
    formatter: default
    class: logging.StreamHandler
    stream: ext://sys.stdout
loggers:
  uvicorn.error:
    level: INFO
    handlers:
      - default
    propagate: no
  uvicorn.access:
    level: INFO
    handlers:
      - access
    propagate: no
```

You'll notice that we are using `ext://...` for `json_default` and`static_fields`. This will load data from other modules such as the one below.

```python title="logging_config.py"
import importlib.metadata
import os


class Dummy:
    pass


def my_json_default(obj: Any) -> Any:
    if isinstance(obj, Dummy):
        return "DUMMY"
    return obj


def get_version_metadata():
    # https://stackoverflow.com/a/78082532
    version = importlib.metadata.version(PROJECT_NAME)
    return version


PROJECT_NAME = 'test-api'
PROJECT_VERSION = get_version_metadata()
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
```

## Logging Expensive to Compute Data

By the nature of Python's logging library, the JSON formatters will only ever run in handlers which are enabled for the given log level. This saves the performance hit of constructing JSON that is never used - but what about the data we pass into the logger? There are two options available to us: using if statements to avoid the call altogether, or using lazy string evaluation libraries.

!!! note
    The below strategies will work for data passed in the `msg` and `extra` arguments.

To avoid the logging calls we use `logger.isEnabledFor` to ensure that we only start constructing our log messages if the logger is enabled:

```python
import logging
import time

from pythonjsonlogger.json import JsonFormatter

def expensive_to_compute():
    time.sleep(5)
    return "world"

## Setup
## -------------------------------------
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

## Log Using isEnabledFor
## -------------------------------------
start = time.time()
if logger.isEnabledFor(logging.INFO):
    logger.info(
        {
            "data": "hello {}".format(expensive_to_compute())
        }
    )
print(f"Logging INFO using isEnabledFor took: {int(time.time() - start)}s")

start = time.time()
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(
        {
            "data": "hello {}".format(expensive_to_compute())
        }
    )
print(f"Logging DEBUG using isEnabledFor took: {int(time.time() - start)}s")
```

For lazy string evaluation we can take advantage of the fact that the default JSON encoders included in this package will call `str` on unkown objects. We can use this to build our own lazy string evaluators, or we can use an existing external package. Pre-existing solutions include: [`lazy-string`](https://pypi.org/project/lazy-string/)'s `LazyString` or [`stringlike`](https://pypi.org/project/stringlike/)'s `CachedLazyString`.

```python
## Log Using lazy-string
## -------------------------------------
from lazy_string import LazyString as L

start = time.time()
logger.info(
    {
        "data": L("hello {}".format, L(expensive_to_compute))
    }
)
print(f"Logging INFO using LazyString took: {int(time.time() - start)}s")

start = time.time()
logger.debug(
    {
        "data": L("hello {}".format, L(expensive_to_compute))
    }
)
print(f"Logging DEBUG using LazyString took: {int(time.time() - start)}s")
```
