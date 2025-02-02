# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### Added
- `exc_info_as_array` and `stack_info_as_array` options are added to `pythonjsonlogger.core.BaseJsonFormatter`.
  - If `exc_info_as_array` is True (Defualt: False), formatter encode exc_info into an array.
  - If `stack_info_as_array` is True (Defualt: False), formatter encode stack_info into an array.

## [3.2.1](https://github.com/nhairs/python-json-logger/compare/v3.2.0...v3.2.1) - 2024-12-16

### Fixed
- Import error on `import pythonjsonlogger.jsonlogger` [#29](https://github.com/nhairs/python-json-logger/issues/29)


## [3.2.0](https://github.com/nhairs/python-json-logger/compare/v3.1.0...v3.2.0) - 2024-12-11

### Changed
- `pythonjsonlogger.[ORJSON,MSGSPEC]_AVAILABLE` no longer imports the respective package when determining availability.
- `pythonjsonlogger.[orjson,msgspec]` now throws a `pythonjsonlogger.exception.MissingPackageError` when required libraries are not available. These contain more information about what is missing whilst still being an `ImportError`.
- `defaults` parameter is no longer ignored and now conforms to the standard library. Setting a defaults dictionary will add the specified keys if the those keys do not exist in a record or weren't passed by the `extra` parameter when logging a message.
- `typing_extensions` is only installed on Python version < 3.10.
- Support Python 3.13
  - `msgspec` has only been tested against pre-release versions.

Thanks @cjwatson and @bharel

## [3.1.0](https://github.com/nhairs/python-json-logger/compare/v3.0.1...v3.1.0) - 2023-05-28

This splits common funcitonality out to allow supporting other JSON encoders. Although this is a large refactor, backwards compatibility has been maintained.

### Added
- `pythonjsonlogger.core` - more details below.
- `pythonjsonlogger.defaults` module that provides many functions for handling unsupported types.
- Orjson encoder support via `pythonjsonlogger.orjson.OrjsonFormatter` with the following additions:
  - bytes are URL safe base64 encoded.
  - Exceptions are "pretty printed" using the exception name and message e.g. `"ValueError: bad value passed"`
  - Enum values use their value, Enum classes now return all values as a list.
  - Tracebacks are supported
  - Classes (aka types) are support
  - Will fallback on `__str__` if available, else `__repr__` if available, else will use `__could_not_encode__`
- MsgSpec encoder support via `pythonjsonlogger.msgspec.MsgspecFormatter` with the following additions:
  - Exceptions are "pretty printed" using the exception name and message e.g. `"ValueError: bad value passed"`
  - Enum classes now return all values as a list.
  - Tracebacks are supported
  - Classes (aka types) are support
  - Will fallback on `__str__` if available, else `__repr__` if available, else will use `__could_not_encode__`
  - Note: msgspec only supprts enum values of type `int` or `str` [jcrist/msgspec#680](https://github.com/jcrist/msgspec/issues/680)

### Changed
- `pythonjsonlogger.jsonlogger` has been moved to `pythonjsonlogger.json` with core functionality moved to `pythonjsonlogger.core`.
- `pythonjsonlogger.core.BaseJsonFormatter` properly supports all `logging.Formatter` arguments:
  - `fmt` is unchanged.
  - `datefmt` is unchanged.
  - `style` can now support non-standard arguments by setting `validate` to `False`
  - `validate` allows non-standard `style` arguments or prevents calling `validate` on standard `style` arguments.
  - `default` is ignored.
- `pythonjsonlogger.json.JsonFormatter` default encodings changed:
  - bytes are URL safe base64 encoded.
  - Exception formatting detected using `BaseException` instead of `Exception`. Now "pretty prints" the exception using the exception name and message e.g. `"ValueError: bad value passed"`
  - Dataclasses are now supported
  - Enum values now use their value, Enum classes now return all values as a list.
  - Will fallback on `__str__` if available, else `__repr__` if available, else will use `__could_not_encode__`
- Renaming fields now preserves order ([#7](https://github.com/nhairs/python-json-logger/issues/7)) and ignores missing fields ([#6](https://github.com/nhairs/python-json-logger/issues/6)).
- Documentation
  - Generated documentation using `mkdocs` is stored in `docs/`
  - Documentation within `README.md` has been moved to `docs/index.md` and `docs/qucikstart.md`.
  - `CHANGELOG.md` has been moved to `docs/change-log.md`
  - `SECURITY.md` has been moved and replaced with a symbolic link to `docs/security.md`.

### Deprecated
- `pythonjsonlogger.jsonlogger` is now `pythonjsonlogger.json`
- `pythonjsonlogger.jsonlogger.RESERVED_ATTRS` is now `pythonjsonlogger.core.RESERVED_ATTRS`.
- `pythonjsonlogger.jsonlogger.merge_record_extra` is now `pythonjsonlogger.core.merge_record_extra`.

### Removed
- Python 3.7 support dropped
- `pythonjsonlogger.jsonlogger.JsonFormatter._str_to_fn` replaced with `pythonjsonlogger.core.str_to_object`.

## [3.0.1](https://github.com/nhairs/python-json-logger/compare/v3.0.0...v3.0.1) - 2023-04-01

### Fixes

- Fix spelling of parameter `json_serialiser` -> `json_serializer` ([#8](https://github.com/nhairs/python-json-logger/issues/8)) - @juliangilbey

## [3.0.0](https://github.com/nhairs/python-json-logger/compare/v2.0.7...v3.0.0) - 2024-03-25

Note: using new major version to seperate changes from this fork and the original (upstream). See [#1](https://github.com/nhairs/python-json-logger/issues/1) for details.

### Changes
- Update supported Python versions - @nhairs
  - Drop 3.6
  - The following versions are supported and tested:
    - CPython 3.7-3.12 (ubuntu, windows, mac)
    - PyPy 3.7-3.10 (ubuntu, wundows, mac)
  - `RESERVED_ATTRS` is now a list and version dependent
- Fix `JsonFormatter.__init__` return type (`None`) - @nhairs
- Moved to `pyproject.toml` - @nhairs
- Update linting and testing - @nhairs
  - Split lint and test steps in GHA
  - Use validate-pyproject, black, pylint, mypy

## [2.0.7](https://github.com/nhairs/python-json-logger/compare/v2.0.6...v2.0.7) - 2023-02-21
### Changed
- Fix inclusion of py.typed in pip packages - @sth
- Added pytest support with test file rename. Migrated to assertEqual

## [2.0.6](https://github.com/nhairs/python-json-logger/compare/v2.0.5...v2.0.6) - 2023-02-14
### Changed
- Parameter `rename_fields` in merge_record_extra is now optional - @afallou

## [2.0.5](https://github.com/nhairs/python-json-logger/compare/v2.0.4...v2.0.5) - 2023-02-12
### Added
- Allow reserved attrs to be renamed - @henkhogan
- Support added for Python 3.11
- Now verifying builds in Pypy 3.9 as well
- Type annotations are now in the package - @louis-jaris
### Changed
- Fix rename_fields for exc_info - @guilhermeferrari
- Cleaned up test file for PEP8 - @lopagela
- Cleaned up old Python 2 artifacts - @louis-jaris
- Dropped Python 3.5 support - @idomozes
- Moved type check via tox into 3.11 run only
- Added test run in Python3.6 (will keep for a little while longer, but it's EOL so upgrade)

## [2.0.4](https://github.com/nhairs/python-json-logger/compare/v2.0.3...v2.0.4) - 2022-07-11
### Changed
- Fix too strict regex for percentage style logging - @aberres

## [2.0.3](https://github.com/nhairs/python-json-logger/compare/v2.0.2...v2.0.3) - 2022-07-08
### Added
- Add PEP 561 marker/basic mypy configuration. - @bringhurst
- Workaround logging.LogRecord.msg type of string. - @bringhurst
### Changed
- Changed a link archive of the reference page in case it's down. - @ahonnecke
- Removed unnecessary try-except around OrderedDict usage - @sozofaan
- Update documentation link to json module + use https - @deronnax
- Dropped 3.5 support. - @bringhurst

## [2.0.2](https://github.com/nhairs/python-json-logger/compare/v2.0.1...v2.0.2) - 2021-07-27
### Added
- Officially supporting 3.9 - @felixonmars.
- You can now add static fields to log objects - @cosimomeli.
### Changed
- Dropped 3.4 support.
- Dropped Travis CI for Github Actions.
- Wheel should build for python 3 instead of just 3.4 now.

## [2.0.1](https://github.com/nhairs/python-json-logger/compare/v2.0.0...v2.0.1) - 2020-10-12
### Added
- Support Pypi long descripton - @ereli-cb
### Changed
- You can now rename output fields - @schlitzered

## [2.0.0](https://github.com/nhairs/python-json-logger/compare/v0.1.11...v2.0.0) - 2020-09-26
### Added
- New Changelog
- Added timezone support to timestamps - @lalten
- Refactored log record to function - @georgysavva
- Add python 3.8 support - @tommilligan
### Removed
- Support for Python 2.7
- Debian directory

## [0.1.11](https://github.com/nhairs/python-json-logger/compare/v0.1.10...v0.1.11) - 2019-03-29
### Added
- Support for Python 3.7
### Changed
- 'stack_info' flag in logging calls is now respected in JsonFormatter by [@ghShu](https://github.com/ghShu)
