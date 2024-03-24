![Build Status](https://github.com/nhairs/python-json-logger/actions/workflows/test-suite.yml/badge.svg)
[![License](https://img.shields.io/pypi/l/python-json-logger.svg)](https://pypi.python.org/pypi/python-json-logger/)
[![Version](https://img.shields.io/pypi/v/python-json-logger.svg)](https://pypi.python.org/pypi/python-json-logger/)

# Python JSON Logger

This library is provided to allow standard python logging to output log data as json objects. With JSON we can make our logs more readable by machines and we can stop writing custom parsers for syslog type records.


### 🚨 Important 🚨

This repository is a maintained fork of [madzak/python-json-logger](https://github.com/madzak/python-json-logger) pending [a PEP 541 request](https://github.com/pypi/support/issues/3607) for the PyPI package.  The future direction of the project is being discussed [here](https://github.com/nhairs/python-json-logger/issues/1).

## Installation

### Install via pip / PyPI

Until the PEP 541 request is complete you will need to use one of the alternative methods below.

### Install from GitHub

```shell
pip install 'python-json-logger@git+https://github.com/nhairs/python-json-logger.git'
```

To install a specific version:

```shell
pip install 'python-json-logger@git+https://github.com/nhairs/python-json-logger.git@v2.0.7'
```


### Install from Source

```shell
git clone https://github.com/nhairs/python-json-logger.git
cd python-json-logger
pip install -e .
```

## Usage

### Integrating with Python's logging framework

Json outputs are provided by the JsonFormatter logging formatter. You can add the custom formatter like below:

**Please note: version 0.1.0 has changed the import structure, please update to the following example for proper importing**

```python
    import logging
    from pythonjsonlogger import jsonlogger

    logger = logging.getLogger()

    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
```

### Customizing fields

The fmt parser can also be overidden if you want to have required fields that differ from the default of just `message`.

These two invocations are equivalent:

```python
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def parse(self):
        return self._fmt.split(';')

formatter = CustomJsonFormatter('one;two')

# is equivalent to:

formatter = jsonlogger.JsonFormatter('%(one)s %(two)s')
```

You can also add extra fields to your json output by specifying a dict in place of message, as well as by specifying an `extra={}` argument.

Contents of these dictionaries will be added at the root level of the entry and may override basic fields.

You can also use the `add_fields` method to add to or generally normalize the set of default set of fields, it is called for every log event. For example, to unify default fields with those provided by [structlog](http://www.structlog.org/) you could do something like this:

```python
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
```

Items added to the log record will be included in *every* log message, no matter what the format requires.

### Adding custom object serialization

For custom handling of object serialization you can specify default json object translator or provide a custom encoder

```python
def json_translate(obj):
    if isinstance(obj, MyClass):
        return {"special": obj.special}

formatter = jsonlogger.JsonFormatter(json_default=json_translate,
                                     json_encoder=json.JSONEncoder)
logHandler.setFormatter(formatter)

logger.info({"special": "value", "run": 12})
logger.info("classic message", extra={"special": "value", "run": 12})
```

### Using a Config File

To use the module with a config file using the [`fileConfig` function](https://docs.python.org/3/library/logging.config.html#logging.config.fileConfig), use the class `pythonjsonlogger.jsonlogger.JsonFormatter`. Here is a sample config file.

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

## Example Output

Sample JSON with a full formatter (basically the log message from the unit test). Every log message will appear on 1 line like a typical logger.

```json
{
    "threadName": "MainThread",
    "name": "root",
    "thread": 140735202359648,
    "created": 1336281068.506248,
    "process": 41937,
    "processName": "MainProcess",
    "relativeCreated": 9.100914001464844,
    "module": "tests",
    "funcName": "testFormatKeys",
    "levelno": 20,
    "msecs": 506.24799728393555,
    "pathname": "tests/tests.py",
    "lineno": 60,
    "asctime": ["12-05-05 22:11:08,506248"],
    "message": "testing logging format",
    "filename": "tests.py",
    "levelname": "INFO",
    "special": "value",
    "run": 12
}
```

## License

This project is licensed under the BSD 2 Clause License - see [`LICENSE`](https://github.com/nhairs/python-json-logger/blob/main/LICENSE)

## Authors and Maintainers

This project was originally authored by [Zakaria Zajac](https://github.com/madzak) and our wonderful [contributors](https://github.com/nhairs/python-json-logger/graphs/contributors)

It is currently maintained by:

- [Nicholas Hairs](https://github.com/nhairs) - [nicholashairs.com](https://www.nicholashairs.com)
