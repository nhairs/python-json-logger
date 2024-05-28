# Quick Start

## Installation

!!! note
    All versions of this fork use version `>=3.0.0`.

    To use pre-fork versions use `python-json-logger<3`.

### Install via pip

Until the PEP 541 request is complete you will need to install directly from github.

#### Install from GitHub

To install from [releases](https://github.com/nhairs/python-json-logger/releases) (including development releases), you can use the URL to the specific wheel.

```shell
# e.g. 3.0.0 wheel
pip install 'python-json-logger@https://github.com/nhairs/python-json-logger/releases/download/v3.0.0/python_json_logger-3.0.0-py3-none-any.whl'
```

## Usage

Python JSON Logger provides [`logging.Formatter`](https://docs.python.org/3/library/logging.html#logging.Formatter) classes that encode the logged message into JSON. Although [a variety of JSON encoders are supported](#alternate-json-encoders), the following examples will use the [JsonFormatter][pythonjsonlogger.json.JsonFormatter] which uses the the `json` module from the standard library.

### Integrating with Python's logging framework

To produce JSON output, attach the formatter to a logging handler:

```python
import logging
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger()

logHandler = logging.StreamHandler()
formatter = JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

### Output fields

#### Required Fields
You can control the logged fields by setting the `fmt` argument when creating the formatter. By default formatters will follow the same `style` of `fmt` as the `logging` module: `%`, `$`, and `{`. All [`LogRecord` attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes) can be output using their name.

```python
formatter = JsonFormatter("{message}{asctime}{exc_info}", style="{")
```

#### Message Fields

Instead of logging a string message you can log using a `dict`.

```python
logger.info({
    "my_data": 1,
    "message": "if you don't include this it will be an empty string",
    "other_stuff": False,
})
```

!!! warning
    Be aware that if you log using a `dict`, other formatters may not be able to handle it.

You can also add additional message fields using the `extra` argument.

```python
logger.info(
    "this logs the same additional fields as above",
    extra={
        "my_data": 1,
        "other_stuff": False,
    },
)
```

Finally, any non-standard attributes added to a `LogRecord` will also be included in the logged data. See [Cookbook: Request / Trace IDs](cookbook.md#request-trace-ids) for an example.

#### Static Fields

Static fields that are added to every log record can be set using the `static_fields` argument.

```python
formatter = JsonFormatter(
    static_fields={"True gets logged on every record?": True}
)
```

### Excluding fields

You can prevent fields being added to the output data by adding them to `reserved_attrs`. By default all [`LogRecord` attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes) are exluded.

```python
from pythonjsonlogger.core import RESERVED_ATTRS

formatter = JsonFormatter(
    reserved_attrs=RESERVED_ATTRS+["request_id", "my_other_field"]
)
```

### Renaming fields

You can rename fields using the `rename_fields` argument.

```python
formatter = JsonFormatter(
    "{message}{levelname}",
    style="{",
    rename_fields={"levelname": "LEVEL"},
)
```

### Custom object serialization

Most formatters support `json_default` which is used to control how objects are serialized.

```python
def my_default(obj):
    if isinstance(obj, MyClass):
        return {"special": obj.special}

formatter = JsonFormatter(json_default=my_default)
```

!!! note
    When providing your own `json_default`, you likely want to call the original `json_default` for your encoder. Python JSON Logger provides custom default serializers for each encoder that tries very hard to ensure sane output is always logged.

### Alternate JSON Encoders

The following JSON encoders are also supported:

- [orjson](https://github.com/ijl/orjson) - [pythonjsonlogger.orjson.OrjsonFormatter][]
- [msgspec](https://github.com/jcrist/msgspec) - [pythonjsonlogger.msgspec.MsgspecFormatter][]
