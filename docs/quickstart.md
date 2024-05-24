# Quick Start

## Installation

Note: All versions of this fork use version `>=3.0.0` - to use pre-fork versions use `python-json-logger<3.0.0`.

### Install via pip

Until the PEP 541 request is complete you will need to install directly from github.

#### Install from GitHub

To install from releases:

```shell
# e.g. 3.0.0 wheel
pip install 'python-json-logger@https://github.com/nhairs/python-json-logger/releases/download/v3.0.0/python_json_logger-3.0.0-py3-none-any.whl'
```

## Usage

Python JSON Logger provides `logging.Formatter`s that encode the logged message into JSON. Although a variety of JSON encoders are supported, in the following examples we will use the [pythonjsonlogger.json.JsonFormatter][] which uses the the `json` module from the standard library.

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

#### Format Fields
You can control the logged fields by setting the `fmt` argument when creating the formatter. By default formatters will follow the same `style` of `fmt` as the `logging` module: `%`, `$`, and `{`. All [`LogRecord` attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes) can be output using their name.

```python
formatter = JsonFormatter("{message}{asctime}{exc_info}", style="{")
```

#### Extra Fields
You can also add extra fields to your json output by specifying a dict in place of message, as well as by specifying an `extra={}` argument. Contents of these dictionaries will be added at the root level of the entry and may override basic fields.

Non-standard attributes added to a `LogRecord` will also be included in the logged data.

#### Static Fields

Static data that is added to every log record can be set using the `static_fields` argument.

```python
formatter = JsonFormatter(static_fields={"True gets logged on every record?": True})
```

### Excluding fields

You can prevent fields being added to the output data by adding them to `reserved_attrs`.

```python
from pythonjsonlogger.core import RESERVED_ATTRS

formatter = JsonFormatter(reserved_attrs=RESERVED_ATTRS+["request_id", "my_other_field"])
```

### Renaming fields

You can rename fields using the `rename_fields` argument.

```python
formatter = JsonFormatter("{message}{levelname}", style="{", rename_fields={"levelname": "LEVEL"})
```

### Custom object serialization

Most formatters support `json_default` which is used to control how objects are serialized.

For custom handling of object serialization you can specify default json object translator or provide a custom encoder

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
