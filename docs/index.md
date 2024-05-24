# Python JSON Logger

<!-- [![PyPi](https://img.shields.io/pypi/v/python-json-logger.svg)](https://pypi.python.org/pypi/python-json-logger/)
[![PyPI - Status](https://img.shields.io/pypi/status/python-json-logger)](https://pypi.python.org/pypi/python-json-logger/)
[![Python Versions](https://img.shields.io/pypi/pyversions/python-json-logger.svg)](https://github.com/nhairs/python-json-logger) -->
[![License](https://img.shields.io/github/license/nhairs/python-json-logger.svg)](https://github.com/nhairs/python-json-logger)
![Build Status](https://github.com/nhairs/python-json-logger/actions/workflows/test-suite.yml/badge.svg)

## Introduction

This library is provided to allow standard python logging to output log data as json objects. With JSON we can make our logs more readable by machines and we can stop writing custom parsers for syslog type records.

!!! warning
    This repository is a maintained fork of [madzak/python-json-logger](https://github.com/madzak/python-json-logger) pending [a PEP 541 request](https://github.com/pypi/support/issues/3607) for the PyPI package.  The future direction of the project is being discussed [here](https://github.com/nhairs/python-json-logger/issues/1).


## Features

- **TODO?:** TODO.
- **Multiple Encoders:** In addition to the standard libary's `json` module, also supports 3rd party encoders: `orjson`, `msgspec`

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

In the case of feature requests, please provide background to the problem you are trying to solve so to help find a solution that makes the most sense for the library as well as your usecase.


## License

This project is licensed under the BSD 2 Clause License - see [`LICENSE`](https://github.com/nhairs/python-json-logger/blob/main/LICENSE)

## Authors and Maintainers

This project was originally authored by [Zakaria Zajac](https://github.com/madzak) and our wonderful [contributors](https://github.com/nhairs/python-json-logger/graphs/contributors)

It is currently maintained by:

- [Nicholas Hairs](https://github.com/nhairs) - [nicholashairs.com](https://www.nicholashairs.com)
