# Cookbook

Recipies for common tasks.

## Include all fields

This can be achieved by setting `reserved_attrs=[]` when creating the formatter.

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
    def process_log_record(log_record):
        new_record = {k[::-1]: v for k, v in log_record.items()}
        return new_record
```


## Request / Trace IDs

There are many ways to add consistent request IDs to your logging. The exact method will depend on your needs and application.

```python
import logging
import uuid
from pythonjsonlogger.json import JsonFormatter

## Setup
## -----------------------------------------------------------------------------
logger = logging.getLogger("test")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

## Solution 1
## -----------------------------------------------------------------------------
formatter = JsonFormatter()
handler.setFormatter(formatter)

def main_1():
    print("========== MAIN 1 ==========")
    for i in range(3):
        request_id = uuid.uuid4().hex
        logger.info("loop start", extra={"request_id": request_id})
        logger.info(f"loop {i}", extra={"request_id": request_id})
        logger.info("loop end", extra={"request_id": request_id})
    return

main_1()

## Solution 2
## -----------------------------------------------------------------------------
REQUEST_ID: str | None = None

def get_request_id() -> str:
    return REQUEST_ID

def generate_request_id():
    global REQUEST_ID
    REQUEST_ID = uuid.uuid4().hex

class RequestIdFilter(logging.Filter):
    # Ref: https://docs.python.org/3/howto/logging-cookbook.html#using-filters-to-impart-contextual-information

    def filter(self, record):
        record.record_id = get_request_id()
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

## Solution 3
## -----------------------------------------------------------------------------
# Reuse REQUEST_ID stuff from solution 2
class MyFormatter(JsonFormatter):
    def process_log_record(self, log_record):
        log_record["request_id"] = get_request_id()
        return log_record

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

### Using `fileConfig`

To use the module with a config file using the [`fileConfig` function](https://docs.python.org/3/library/logging.config.html#logging.config.fileConfig), use the class `pythonjsonlogger.json.JsonFormatter`. Here is a sample config file.

```ini
[loggers]
keys = root,custom

[logger_root]
handlers =

[logger_custom]
level = INFO
handlers = custom
qualname = custom

[handlers]
keys = custom

[handler_custom]
class = StreamHandler
level = INFO
formatter = json
args = (sys.stdout,)

[formatters]
keys = json

[formatter_json]
format = %(message)s
class = pythonjsonlogger.jsonlogger.JsonFormatter
```

