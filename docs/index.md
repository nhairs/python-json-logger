# Python JSON Logger

[![PyPi](https://img.shields.io/pypi/v/python-json-logger.svg)](https://pypi.python.org/pypi/python-json-logger/)
[![PyPI - Status](https://img.shields.io/pypi/status/python-json-logger)](https://pypi.python.org/pypi/python-json-logger/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-json-logger)](https://pypi.python.org/pypi/python-json-logger/)
[![Python Versions](https://img.shields.io/pypi/pyversions/python-json-logger.svg)](https://github.com/nhairs/python-json-logger)
[![License](https://img.shields.io/github/license/nhairs/python-json-logger.svg)](https://github.com/nhairs/python-json-logger)
![Build Status](https://github.com/nhairs/python-json-logger/actions/workflows/test-suite.yml/badge.svg)

## Introduction

Python JSON Logger enables you produce JSON logs when using Python's `logging` package.

JSON logs are machine readable allowing for much easier parsing and ingestion into log aggregation tools.

This library assumes that you are famliar with the `logging` standard library package; if you are not you should start by reading the official [Logging HOWTO](https://docs.python.org/3/howto/logging.html).


## Features

- **Standard Library Compatible:** Implement JSON logging without modifying your existing log setup.
- **Supports Multiple JSON Encoders:** In addition to the standard libary's `json` module, also supports the [`orjson`][pythonjsonlogger.orjson], [`msgspec`][pythonjsonlogger.msgspec] JSON encoders.
- **Fully Customizable Output Fields:** Control required, excluded, and static fields including automatically picking up custom attributes on `LogRecord` objects. Fields can be renamed before they are output.
- **Encode Any Type:** Encoders are customized to ensure that something sane is logged for any input including those that aren't supported by default. For example formatting UUID objects into their string representation and bytes objects into a base 64 encoded string.

## Quick Start

Follow our [Quickstart Guide](quickstart.md).

```python title="TLDR"
import logging
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger.addHandler(handler)

logger.info("Logging using pythonjsonlogger!", extra={"more_data": True})

# {"message": "Logging using pythonjsonlogger!", "more_data": true}
```


## Bugs, Feature Requests etc
Please [submit an issue on github](https://github.com/nhairs/python-json-logger/issues).

In the case of bug reports, please help us help you by following best practices [^1^](https://marker.io/blog/write-bug-report/) [^2^](https://www.chiark.greenend.org.uk/~sgtatham/bugs.html).

In the case of feature requests, please provide background to the problem you are trying to solve so that we can a solution that makes the most sense for the library as well as your use case.

## License

This project is licensed under the BSD 2 Clause License - see [`LICENSE`](https://github.com/nhairs/python-json-logger/blob/main/LICENSE)

## Authors and Maintainers

This project was originally authored by [Zakaria Zajac](https://github.com/madzak) and our wonderful [contributors](https://github.com/nhairs/python-json-logger/graphs/contributors)

It is currently maintained by:

- [Nicholas Hairs](https://github.com/nhairs) - [nicholashairs.com](https://www.nicholashairs.com)
