"""Core functionality shared by all JSON loggers"""

### IMPORTS
### ============================================================================
## Future
from __future__ import annotations

## Standard Library
from datetime import datetime, timezone
import importlib
import logging
import re
import sys
from typing import Optional, Union, Callable, List, Dict, Container, Any, Sequence

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

## Installed

## Application


### CONSTANTS
### ============================================================================
# skip natural LogRecord attributes
# http://docs.python.org/library/logging.html#logrecord-attributes
# Changed in 3.0.0, is now list[str] instead of tuple[str, ...]
RESERVED_ATTRS: List[str] = [
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
]

if sys.version_info >= (3, 12):
    # taskName added in python 3.12
    RESERVED_ATTRS.append("taskName")
    RESERVED_ATTRS.sort()


STYLE_STRING_TEMPLATE_REGEX = re.compile(r"\$\{(.+?)\}", re.IGNORECASE)
STYLE_STRING_FORMAT_REGEX = re.compile(r"\{(.+?)\}", re.IGNORECASE)
STYLE_PERCENT_REGEX = re.compile(r"%\((.+?)\)", re.IGNORECASE)

## Type Aliases
## -----------------------------------------------------------------------------
OptionalCallableOrStr: TypeAlias = Optional[Union[Callable, str]]
LogRecord: TypeAlias = Dict[str, Any]


### FUNCTIONS
### ============================================================================
def str_to_object(obj: Any) -> Any:
    """Import strings to an object, leaving non-strings as-is.

    Args:
        obj: the object or string to process

    *New in 4.0*
    """

    if not isinstance(obj, str):
        return obj

    module_name, attribute_name = obj.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), attribute_name)


def merge_record_extra(
    record: logging.LogRecord,
    target: Dict,
    reserved: Container[str],
    rename_fields: Optional[Dict[str, str]] = None,
) -> Dict:
    """
    Merges extra attributes from LogRecord object into target dictionary

    :param record: logging.LogRecord
    :param target: dict to update
    :param reserved: dict or list with reserved keys to skip
    :param rename_fields: an optional dict, used to rename field names in the output.
            Rename levelname to log.level: {'levelname': 'log.level'}

    *Changed in 4.0*: `reserved` is now `Container[str]`.
    """
    if rename_fields is None:
        rename_fields = {}
    for key, value in record.__dict__.items():
        # this allows to have numeric keys
        if key not in reserved and not (hasattr(key, "startswith") and key.startswith("_")):
            target[rename_fields.get(key, key)] = value
    return target


### CLASSES
### ============================================================================
class BaseJsonFormatter(logging.Formatter):
    """Base class for pythonjsonlogger formatters

    Must not be used directly
    """

    _style: Union[logging.PercentStyle, str]  # type: ignore[assignment]

    ## Parent Methods
    ## -------------------------------------------------------------------------
    # pylint: disable=too-many-arguments,super-init-not-called
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        validate: bool = True,
        *,
        defaults: None = None,
        prefix: str = "",
        rename_fields: Optional[Dict[str, str]] = None,
        static_fields: Optional[Dict[str, Any]] = None,
        reserved_attrs: Optional[Sequence[str]] = None,
        timestamp: Union[bool, str] = False,
    ) -> None:
        """
        Args:
            fmt: string representing fields to log
            datefmt: format to use when formatting asctime field
            style: how to extract log fields from `fmt`
            validate: validate fmt against style, if implementing a custom style you
                must set this to `False`.
            defaults: ignored - kept for compatibility
            prefix: an optional string prefix added at the beginning of
                the formatted string
            rename_fields: an optional dict, used to rename field names in the output.
                Rename message to @message: {'message': '@message'}
            static_fields: an optional dict, used to add fields with static values to all logs
            reserved_attrs: an optional list of fields that will be skipped when
                outputting json log record. Defaults to all log record attributes:
                http://docs.python.org/library/logging.html#logrecord-attributes
            timestamp: an optional string/boolean field to add a timestamp when
                outputting the json log record. If string is passed, timestamp will be added
                to log record using string as key. If True boolean is passed, timestamp key
                will be "timestamp". Defaults to False/off.

        *Changed in 4.0*: you can now use custom values for style by setting validate to `False`.
        The value is stored in `self._style` as a string. The `parse` method will need to be
        overridden in order to support the new style.
        """
        ## logging.Formatter compatibility
        ## ---------------------------------------------------------------------
        if style in logging._STYLES:
            _style = logging._STYLES[style][0](fmt, defaults=defaults)  # type: ignore[operator]
            if validate:
                _style.validate()
            self._style = _style
            self._fmt = _style._fmt

        elif not validate:
            self._style = style
            self._fmt = fmt

        else:
            raise ValueError(f"Style must be one of: {','.join(logging._STYLES.keys())}")

        self.datefmt = datefmt

        ## JSON Logging specific
        ## ---------------------------------------------------------------------
        self.prefix = prefix
        self.rename_fields = rename_fields if rename_fields is not None else {}
        self.static_fields = static_fields if static_fields is not None else {}
        self.reserved_attrs = set(reserved_attrs if reserved_attrs is not None else RESERVED_ATTRS)
        self.timestamp = timestamp

        self._required_fields = self.parse()
        self._skip_fields = set(self._required_fields)
        self._skip_fields.update(self.reserved_attrs)
        return

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record and serializes to json"""
        message_dict: Dict[str, Any] = {}
        # TODO: logging.LogRecord.msg and logging.LogRecord.message in typeshed
        #        are always type of str. We shouldn't need to override that.
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = ""
        else:
            record.message = record.getMessage()
        # only format time if needed
        if "asctime" in self._required_fields:
            record.asctime = self.formatTime(record, self.datefmt)

        # Display formatted exception, but allow overriding it in the
        # user-supplied dict.
        if record.exc_info and not message_dict.get("exc_info"):
            message_dict["exc_info"] = self.formatException(record.exc_info)
        if not message_dict.get("exc_info") and record.exc_text:
            message_dict["exc_info"] = record.exc_text
        # Display formatted record of stack frames
        # default format is a string returned from :func:`traceback.print_stack`
        if record.stack_info and not message_dict.get("stack_info"):
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        log_record: LogRecord = {}
        self.add_fields(log_record, record, message_dict)
        log_record = self.process_log_record(log_record)

        return self.serialize_log_record(log_record)

    ## JSON Formatter Specific Methods
    ## -------------------------------------------------------------------------
    def parse(self) -> List[str]:
        """Parses format string looking for substitutions

        This method is responsible for returning a list of fields (as strings)
        to include in all log messages.

        You can support custom styles by overriding this method.
        """
        if isinstance(self._style, logging.StringTemplateStyle):
            formatter_style_pattern = STYLE_STRING_TEMPLATE_REGEX

        elif isinstance(self._style, logging.StrFormatStyle):
            formatter_style_pattern = STYLE_STRING_FORMAT_REGEX

        elif isinstance(self._style, logging.PercentStyle):
            # PercentStyle is parent class of StringTemplateStyle and StrFormatStyle
            # so it must be checked last.
            formatter_style_pattern = STYLE_PERCENT_REGEX

        else:
            raise ValueError(f"Style {self._style!r} is not supported")

        if self._fmt:
            return formatter_style_pattern.findall(self._fmt)

        return []

    def serialize_log_record(self, log_record: LogRecord) -> str:
        """Returns the final representation of the log record.

        Args:
            log_record: the log record
        """
        return self.prefix + self.jsonify_log_record(log_record)

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        Override this method to implement custom logic for adding fields.
        """
        for field in self._required_fields:
            log_record[field] = record.__dict__.get(field)

        log_record.update(self.static_fields)
        log_record.update(message_dict)
        merge_record_extra(
            record,
            log_record,
            reserved=self._skip_fields,
            rename_fields=self.rename_fields,
        )

        if self.timestamp:
            # TODO: Can this use isinstance instead?
            # pylint: disable=unidiomatic-typecheck
            key = self.timestamp if type(self.timestamp) == str else "timestamp"
            log_record[key] = datetime.fromtimestamp(record.created, tz=timezone.utc)

        self._perform_rename_log_fields(log_record)
        return

    def _perform_rename_log_fields(self, log_record: Dict[str, Any]) -> None:
        for old_field_name, new_field_name in self.rename_fields.items():
            log_record[new_field_name] = log_record[old_field_name]
            del log_record[old_field_name]
        return

    # Child Methods
    # ..........................................................................
    def jsonify_log_record(self, log_record: LogRecord) -> str:
        """Convert this log record into a JSON string.

        Child classes MUST override this method.
        """
        raise NotImplementedError()

    def process_log_record(self, log_record: LogRecord) -> LogRecord:
        """Custom processing of the log record.

        Child classes can override this method to alter the log record before it
        is serialized.
        """
        return log_record
