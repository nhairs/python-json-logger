# Graylog

Graylog offers different input protocols. This recipe sends JSON as the body of a syslog message. A syslog input parses the envelope, then a JSON extractor or processing pipeline extracts application fields from the body.

## Format the application payload

Prefix application fields to avoid colliding with Graylog's native `message`, `timestamp`, `source`, and numeric `level` fields:

```python
import logging

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter(
    "%(message)s %(levelname)s %(name)s",
    rename_fields={
        "message": "app_message",
        "levelname": "app_level",
        "name": "app_logger",
        "exc_info": "app_exception",
    },
    static_fields={"app_service": "billing", "app_environment": "dev"},
    timestamp="app_timestamp",
)
record = logging.makeLogRecord(
    {
        "name": "billing",
        "msg": "Payment accepted",
        "args": (),
        "levelname": "INFO",
        "levelno": logging.INFO,
        "created": 1500000000.125,
    }
)
print(formatter.format(record))
```

```json
{"app_message": "Payment accepted", "app_level": "INFO", "app_logger": "billing", "app_service": "billing", "app_environment": "dev", "app_timestamp": "2017-07-14T02:40:00.125000+00:00"}
```

This is the JSON body, before a delivery method adds its envelope. Prefix additional context supplied through `extra` in the same way, such as `app_request_id`.

## Delivery options

| Method | When to choose it | Receiving setup |
| --- | --- | --- |
| [Syslog](../delivery/syslog.md) | You have a syslog relay or can configure a syslog input | Matching syslog UDP input, UTC header interpretation, and JSON parsing of the message body |
| [Files](../delivery/files.md) or [stdout/stderr](../delivery/streams.md) | An existing forwarder collects the application logs | Forwarder sends to a matching Graylog input, preserving JSON or transforming it to that input's protocol |
| [HTTP sender](../delivery/handlers.md) | A client already emits GELF | GELF HTTP input; requires a different event schema |

For the syslog route, use this page's `formatter` as the payload formatter inside `SyslogEnvelope` from the shared [syslog recipe](../delivery/syslog.md). Configure a [Graylog syslog input](https://go2docs.graylog.org/current/getting_in_log_data/syslog_inputs.html) on the matching address, port, and UDP transport. Its `message` field should contain the JSON body after header/tag parsing. Use a [JSON extractor](https://go2docs.graylog.org/current/making_sense_of_your_log_data/extractors.htm) on that field to expose `app_*` fields.

The native severity comes from syslog priority; `app_level` retains Python's text. `app_timestamp` preserves the full UTC event time. Merely extracting it does not replace Graylog's native timestamp: use explicit receiver-side date parsing and assignment if you need that behavior.

For file or runtime collection, choose a forwarder with an output compatible with your Graylog input. A [raw/plaintext input](https://go2docs.graylog.org/current/getting_in_log_data/raw_or_plaintext_input.html) can receive JSON from a suitably framed sender, but requires parsing. If the forwarder emits GELF instead, it must map the event into GELF fields.

[GELF](https://go2docs.graylog.org/current/getting_in_log_data/gelf_format.html) has its own required fields, numeric severity, timestamp representation, additional-field conventions, and transport framing. Attaching this formatter to `SysLogHandler` or `HTTPHandler` does not implement GELF. See the [handler compatibility notes](../delivery/handlers.md).
