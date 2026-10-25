# Cloud platform appendix

Managed platforms often collect stdout/stderr or files automatically. First identify the platform's collection path, then configure the formatter's payload fields. The same provider can have different rules for container capture, host agents, and direct ingestion APIs.

These notes describe native integration options separately from the guide's community-selected destinations. They are not a ranking or endorsement.

## AWS CloudWatch Logs

Use the shared [stream](delivery/streams.md) recipe when the runtime captures container or function output, or the [file](delivery/files.md) recipe with a host agent. Configure the runtime or agent to forward records to your log group and stream.

[CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html) can discover fields inside supported JSON events. Its system fields, including `@timestamp` and `@message`, belong to the CloudWatch event representation; renaming application fields to those names does not set the ingestion envelope. Keep application event time in an explicit field and configure the collection path to use it where supported.

See the [CloudWatch agent file collection configuration](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html) for file paths and timestamp parsing. Direct APIs have separate event and authentication requirements; do not infer them from a stream recipe.

## Google Cloud Logging

For a managed runtime that supports structured stdout/stderr, use the shared [stream recipe](delivery/streams.md). For host file collection, use the [file recipe](delivery/files.md) and configure the Ops Agent to parse JSON.

The [structured logging reference](https://docs.cloud.google.com/logging/docs/structured-logging) describes recognized fields such as `severity`, `message`, time fields, and `logging.googleapis.com/trace`. Rename `levelname` to `severity` for severity recognition. Use full UTC timestamps as described in [Logging Time](../time.md), then match the time field to your actual collection path. Trace correlation requires the documented trace identifier format, not an arbitrary request ID.

Some fields move into the Cloud Logging entry envelope, while other application data remains in `jsonPayload`. Follow the [Ops Agent structured-log instructions](https://docs.cloud.google.com/logging/docs/agent/ops-agent/configuration#logging-processors) for parsing and field mapping instead of assuming identical behavior in all Google runtimes.

## Azure Monitor Logs

Use [JSON files](delivery/files.md) with a configured Azure Monitor Agent collection rule, or [streams](delivery/streams.md) where the hosting service captures console output. Choose the receiving table and schema for the actual collection path.

[JSON file collection](https://learn.microsoft.com/en-us/azure/azure-monitor/vm/data-collection-log-json) uses a data collection rule and can transform the event's timestamp into `TimeGenerated`. [Direct Logs ingestion](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal/) also requires a matching collection rule and table schema. Renaming an application field to `TimeGenerated` alone does not configure either path. Keep JSON values compatible with the declared column types, and map message, severity, and context fields explicitly.

For every provider, follow its collection instructions for credentials, routing, timestamp behavior, and deployment constraints. This library formats the application payload; it does not create cloud resources or provision delivery.
