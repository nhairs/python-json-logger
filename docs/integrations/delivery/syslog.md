# Send JSON through syslog

Use syslog when your environment already has a relay, or when the destination offers a syslog input. Match the sender's transport, header, encoding, and framing to that receiver. A JSON body alone is not a complete RFC 3164 or RFC 5424 syslog message.

## Send UDP messages with an RFC 3164 header

This example targets a receiver on `127.0.0.1:1514`. Start a local syslog relay or a destination syslog UDP input there before running it. For a remote receiver, replace the address with its hostname and configured port.

`SysLogHandler` supplies the priority prefix. The wrapper below supplies the timestamp, hostname, and application tag while delegating the JSON body to your chosen destination formatter:

```python
import logging
import socket
import time
from logging.handlers import SysLogHandler

from pythonjsonlogger.json import JsonFormatter


class SyslogEnvelope(logging.Formatter):
    """Wrap a destination formatter's output in an RFC 3164 header."""

    converter = time.gmtime

    def __init__(self, payload_formatter: logging.Formatter) -> None:
        super().__init__()
        self.payload_formatter = payload_formatter
        self.hostname = socket.gethostname()
        return None

    def format(self, record: logging.LogRecord) -> str:
        # RFC 3164 uses a space-padded day and an English month abbreviation.
        created = self.converter(record.created)
        month = (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )[created.tm_mon - 1]
        timestamp = (
            f"{month} {created.tm_mday:2d} "
            f"{created.tm_hour:02d}:{created.tm_min:02d}:{created.tm_sec:02d}"
        )
        payload = self.payload_formatter.format(record)
        return f"{timestamp} {self.hostname} billing: {payload}"


formatter = JsonFormatter("%(message)s %(levelname)s")
handler = SysLogHandler(
    address=("127.0.0.1", 1514),
    facility=SysLogHandler.LOG_USER,
    socktype=socket.SOCK_DGRAM,
)
handler.append_nul = False
handler.setFormatter(SyslogEnvelope(formatter))

logger = logging.getLogger("syslog-example")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(handler)
logger.info("Ready")
handler.close()
logger.removeHandler(handler)
```

A representative UDP datagram is:

```text
<14>Jul 14 02:40:00 app-host billing: {"message": "Ready", "levelname": "INFO"}
```

The timestamp and hostname vary. Priority `14` combines the user facility with INFO's syslog severity `6`. The receiver removes the header and tag before parsing the JSON body. The example uses UTC, but an RFC 3164 timestamp has no year or timezone: configure the receiver for UTC and retain a full event timestamp in the payload when you need it.

## Match the receiver

`append_nul=False` omits the NUL byte that some older syslog receivers expect. Set it according to the receiver; otherwise it may appear in the body or affect parsing. The UDP datagram is the message boundary, so this recipe adds no newline delimiter.

TCP receivers need agreed framing, such as newline termination, NUL termination, or octet counting. Changing only `socktype` does not configure those requirements. Use a local relay when you need its framing, TLS, buffering, or retry support. For a Unix-domain relay socket, use its actual path, such as `/dev/log`, rather than assuming that path exists on every platform.

UDP can lose messages, and large JSON events or exceptions may exceed receiver or network limits. Choose a [stream](streams.md) or [file](files.md) collector route when those constraints do not fit your application.

## Choose a destination

The [Graylog recipe](../destinations/graylog.md) supplies a formatter whose application fields avoid collisions with native syslog fields. Wrap that formatter with `SyslogEnvelope` in place of the example formatter above. Graylog needs a matching syslog input and JSON parsing of the extracted message body. This route does not produce GELF.

Other destination pages list their documented routes in the [compatibility table](../index.md#choose-a-delivery-route). See [Python's syslog handler reference](https://docs.python.org/3/library/logging.handlers.html#sysloghandler) for platform and handler behavior.
