# Loki and Grafana Cloud

Use the same application JSON for self-hosted Loki and Grafana Cloud Logs. A collector such as Alloy supplies Loki's stream labels, event timestamps, endpoint, and credentials.

## Format the event

These payload names are conventions for this recipe, not mandatory Loki fields:

```python
import logging

from pythonjsonlogger.json import JsonFormatter

formatter = JsonFormatter(
    "%(message)s %(levelname)s %(name)s",
    rename_fields={"levelname": "level", "name": "logger"},
    static_fields={"service": "billing", "environment": "dev"},
    timestamp=True,
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
{"message": "Payment accepted", "level": "INFO", "logger": "billing", "service": "billing", "environment": "dev", "timestamp": "2017-07-14T02:40:00.125000+00:00"}
```

Attach this formatter to a handler using a delivery recipe below. Exceptions appear as `exc_info` strings; request IDs and other application context can be supplied through `extra`.

## Delivery options

| Method | When to choose it | Receiving setup |
| --- | --- | --- |
| [stdout/stderr](../delivery/streams.md) | The container runtime already captures logs | Alloy collects runtime output, unwraps its envelope, then parses the JSON |
| [Files](../delivery/files.md) | A host agent can tail application files | Alloy discovers the file paths and reads each JSON line |
| [HTTP sender](../delivery/handlers.md) | An existing client already implements Loki push | The client builds Loki's streams envelope; plain application JSON is insufficient |

Use the official [Alloy Kubernetes collection guide](https://grafana.com/docs/alloy/latest/collect/logs-in-kubernetes/) or [file source reference](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/) for collection. Configure [loki.process](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.process/) to parse `timestamp` as RFC 3339 event time if you want application time rather than collection time. Keep the JSON body available for querying.

Explicitly set a stable service label, such as `service_name="billing"`, and optionally an environment label. Adding `service` to application JSON does not itself create a label. [Loki's label guidance](https://grafana.com/docs/loki/latest/get-started/labels/) explains stream identity and structured metadata. Keep request IDs, trace IDs, and other values with many distinct values in the payload or structured metadata rather than indexed labels.

After collection is configured, a query such as `{service_name="billing"} | json | level="INFO"` can check parsed fields. Use recent events when checking ingestion: the fixed historical timestamp above is only for demonstrating formatter output.

For direct delivery, follow the [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/) and the [HTTP handler compatibility notes](../delivery/handlers.md). For Grafana Cloud, use the endpoint and credentials supplied for your stack rather than a self-hosted endpoint.
