# Integrations

Choose the fields your destination understands and a delivery method that fits your deployment. Python JSON Logger formats events; a handler writes them, and a collector or receiver gets them into your logging system:

```text
LogRecord -> JSON formatter -> handler -> collector or receiver -> destination
```

Start with [fields](fields.md), choose a destination below, then follow its links to a reusable delivery recipe. You can use the same destination formatter with different handlers, or send to different destinations through the same collection infrastructure.

## Choose a delivery route

**Recipe** means this guide supplies Python setup and describes the receiving side. **Intermediary** means a collector, relay, or ingestion client must also be configured using the linked official instructions. **Not covered** means this guide does not document that combination, rather than that the product cannot support it.

| Destination | [stdout/stderr](delivery/streams.md) | [Files](delivery/files.md) | [Syslog](delivery/syslog.md) | [HTTP](delivery/handlers.md) |
| --- | --- | --- | --- | --- |
| [Loki / Grafana Cloud](destinations/loki.md#delivery-options) | Recipe + Alloy | Recipe + Alloy | Not covered | Intermediary: Loki client |
| [Graylog](destinations/graylog.md#delivery-options) | Intermediary: forwarder | Intermediary: forwarder | Recipe + syslog input | Intermediary: GELF sender |
| [OpenObserve](destinations/openobserve.md#delivery-options) | Recipe + forwarder | Recipe + forwarder | Not covered | Intermediary: HTTP sender |
| [Seq](destinations/seq.md#delivery-options) | Recipe + seqcli | Recipe + seqcli | Not covered | Intermediary: HTTP sender |

The stream and file recipes produce newline-delimited JSON: one object per physical line. The syslog recipe wraps each JSON object in a syslog message. HTTP endpoints may require a different envelope or batching format even when the event fields are identical.

Each destination page explains receiver prerequisites, parsing, and event-time handling. Collector configuration is linked to official documentation. The Python examples can be checked locally; the guide does not establish end-to-end validation against running backends.

## Why these destinations?

The initial set covers open-source logging systems, hosted services, and commercial software: Loki with Grafana Cloud, Graylog, OpenObserve, and Seq. It also exercises different conventions: schema-light JSON, syslog, and Compact Log Event Format (CLEF).

This is a practical selection, not a popularity ranking. Independent users describe using and recommending these tools in discussions about [self-hosted logging](https://www.reddit.com/r/selfhosted/comments/1gldrle/) and [logging workflows](https://www.reddit.com/r/selfhosted/comments/1nflusl/logs_what_are_we_using/). Those reports are qualitative and include operational complaints as well as praise. Maintainer announcements and vendor claims are not independent evidence of user satisfaction.

For future additions, look for repeated independent accounts of real use, active maintenance, and documented ingestion paths. Download counts, GitHub stars, marketing, and adoption alone do not establish that a community values a tool. Recheck those signals when extending the guide.

See also [Elastic, OpenSearch, and OpenTelemetry compatibility](compatibility.md) and the separate [cloud platform appendix](cloud.md).
