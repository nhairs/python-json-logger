# HTTP and other handlers

A handler must actually use its formatter for `setFormatter(JsonFormatter(...))` to affect the transmitted payload. Check both handler behavior and the destination's ingestion protocol before choosing a direct network route.

| Handler | Effect of attaching a JSON formatter |
| --- | --- |
| `StreamHandler` and file handlers | Write formatted JSON followed by the configured terminator; see [streams](streams.md) and [files](files.md) |
| `SysLogHandler` | Uses formatted output as the message body and supplies a priority prefix; see [headers and framing](syslog.md) |
| `HTTPHandler` | Uses `mapLogRecord` and URL encoding; does not call the formatter to build a JSON request |
| `SocketHandler` / `DatagramHandler` | Serialize record data using pickle; do not send the formatter's JSON as the wire payload |
| Third-party handlers | Depends on the implementation; some serialize records themselves or expect a particular formatter |

These behaviors are described in [Python's handler reference](https://docs.python.org/3/library/logging.handlers.html). Overriding `HTTPHandler.mapLogRecord` alone still leaves its URL encoding behavior in place.

## Choose an HTTP sender

Use a destination-supported handler/client, or let a collector read [streams](streams.md) or [files](files.md) and handle forwarding. Before attaching this library's formatter to a third-party handler, verify that it calls `format(record)` and does not double-encode the result as a quoted JSON string.

Destination-specific requirements:

- [Loki](../destinations/loki.md#delivery-options): the push API needs a streams envelope with labels and timestamped entries.
- [Graylog](../destinations/graylog.md#delivery-options): the GELF HTTP input needs a GELF event, not the JSON-in-syslog payload.
- [OpenObserve](../destinations/openobserve.md#delivery-options): the JSON endpoint accepts a batch array; the multi-line endpoint has different framing.
- [Seq](../destinations/seq.md#delivery-options): CLEF ingestion accepts newline-delimited events and uses its specified content type.

Use the linked destination instructions for endpoint authentication, batching, retries, size limits, and failure handling. Formatting an event does not implement those delivery responsibilities. This guide does not implement an HTTP handler.
