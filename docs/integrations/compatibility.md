# Other formats and destinations

The shared [stream](delivery/streams.md) and [file](delivery/files.md) recipes also work with other collectors. Match the destination's schema and protocol instead of assuming that all JSON logging systems interpret the same keys.

## Elastic and OpenSearch

Elastic Common Schema (ECS) uses names such as `@timestamp`, `message`, `log.level`, and `service.name`. You can select and rename source fields with Python JSON Logger, but renaming alone does not implement ECS's nested objects, severity normalization, exception structure, or other metadata.

For example, `rename_fields={"levelname": "log.level"}` produces a literal dotted key. Whether that key is expanded or accepted depends on the collector and index mapping. An actual nested object requires an explicit formatter or collector transformation. Follow [Elastic's Python log ingestion guide](https://www.elastic.co/docs/manage-data/ingest/ingesting-data-from-applications/ingest-logs-from-python-application-using-filebeat) for its receiving configuration. For complete ECS formatting, consider the [official ECS Python formatter](https://www.elastic.co/docs/reference/ecs/logging/python).

OpenSearch has its own collectors, ingestion pipelines, and mappings. Sharing an ancestry with Elasticsearch does not guarantee compatibility with every Elastic agent, ECS version, or API. Follow [OpenSearch log ingestion documentation](https://docs.opensearch.org/latest/observing-your-data/log-ingestion/) for your deployment. Configure JSON decoding and the event timestamp explicitly, and verify the index mapping against your actual output.

## OpenTelemetry

The [OpenTelemetry logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) separates event time, observed time, severity, body, attributes, resource information, and trace context. A collector can parse application JSON from files or runtime logs and map it into that model before exporting OTLP.

Renaming `message` to `body` does not produce an OTLP envelope. Python's `levelno` values also differ from OpenTelemetry severity numbers. Configure explicit severity conversion, event-time parsing, resource attributes, and valid trace/span identifiers in your collector. Alternatively, use an OpenTelemetry logging bridge and exporter, whose serialization path does not require a JSON formatter. See the [OpenTelemetry Collector filelog receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/filelogreceiver) for JSON parsing and file collection.

For native AWS, Google Cloud, or Azure collection, see the separate [cloud platform appendix](cloud.md).
