# Write JSON files

Use files when a collector tails local logs, or when you need a local copy before forwarding. Ensure the application can write the directory and the collector can read it. A file handler does not send logs to a remote destination.

## Rotate files in the application

```python
import logging
from logging.handlers import RotatingFileHandler

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter("%(message)s %(levelname)s", json_ensure_ascii=False)
handler = RotatingFileHandler(
    "application.jsonl", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
)
handler.setFormatter(formatter)

logger = logging.getLogger("file-example")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(handler)
logger.info("Payment accepted: café")
handler.close()
logger.removeHandler(handler)
```

The file contains one JSON object per line:

```json
{"message": "Payment accepted: café", "levelname": "INFO"}
```

Replace `formatter` with your destination formatter. The handler appends to the file and retains up to five backups when it rotates. Closing it here makes the standalone example self-contained; a running application should retain its handler until shutdown.

Configure your collector's file discovery and rotation handling to avoid missing or rereading rotated events. Multiple processes should not rotate the same file using independent instances of this handler. See the [logging cookbook's multi-process guidance](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes).

## Use external rotation

On Unix, choose `WatchedFileHandler` when a tool such as logrotate owns rotation. This complete example writes the same shape of event:

```python
import logging
from logging.handlers import WatchedFileHandler

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter("%(message)s %(levelname)s", json_ensure_ascii=False)
handler = WatchedFileHandler("application.jsonl", encoding="utf-8")
handler.setFormatter(formatter)

logger = logging.getLogger("watched-file-example")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(handler)
logger.info("Payment accepted: café")
handler.close()
logger.removeHandler(handler)
```

`WatchedFileHandler` reopens a file when its device or inode changes. It does not perform rotation and is not appropriate for Windows. See the [handler reference](https://docs.python.org/3/library/logging.handlers.html#watchedfilehandler) for platform behavior. Choose one rotation owner for a file.

## Forward the files

Keep compact JSON and the newline terminator. Leave exceptions as escaped strings inside the JSON object, rather than configuring a collector to join traceback lines. A parsed exception string can contain newlines while the serialized event remains on one physical line.

- [Loki / Grafana Cloud](../destinations/loki.md#delivery-options): Alloy tails the JSON file.
- [OpenObserve](../destinations/openobserve.md#delivery-options): a forwarder tails, parses, and ships the file.
- [Seq](../destinations/seq.md#delivery-options): `seqcli` imports files produced with the CLEF formatter.
- [Graylog](../destinations/graylog.md#delivery-options): a forwarder sends file events to a compatible input.
