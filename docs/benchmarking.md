# Benchmarking

Compare the default `JsonFormatter`, `OrjsonFormatter`, and `MsgspecFormatter`
with the opt-in benchmark suite. Measurements cover serialization and complete
record formatting. They help you choose a backend for a workload; they do not
predict application throughput or handler I/O performance.

## Run benchmarks

From a repository checkout, install the benchmark dependencies:

```shell
uv sync --python 3.15 --no-default-groups --group benchmark
```

All three backends are required. An unavailable dependency fails installation or
collection instead of silently removing it from the comparison. Standard
GIL-enabled CPython 3.10–3.15 is the published benchmark matrix.

Check every case without collecting performance measurements:

```shell
uv run --no-sync pytest benchmarks --benchmark-disable
```

Collect measurements with warmup and export the results:

```shell
mkdir -p benchmark-results
uv run --no-sync pytest benchmarks --benchmark-warmup=on \
  --benchmark-json=benchmark-results/python-3.15.json
```

You can also use `uvx tox -e benchmark`. This writes JSON to the environment's
`envtmpdir` (normally `.tox/benchmark/tmp/benchmark.json`). Pass pytest options
after `--` to select cases or change measurement settings. For example, use
`-k unicode` to select Unicode workloads. Normal test runs collect only `tests/`
and do not need the benchmark dependencies.

The manual **Benchmark JSON formatters** GitHub Actions workflow runs Linux
x86-64 jobs for Python 3.10–3.15. Each job measures all backends on the same
runner and uploads its JSON results as an artifact. Its job summary contains the
comparison table. Timing differences never fail CI.

## Measurement methodology

The suite uses `pytest-benchmark` for pytest integration, automatic calibration,
statistics, and JSON export. `pyperf` was considered for its worker-process
isolation and instability diagnostics; pytest integration was preferred for this
initial suite. Run on an otherwise idle machine, use warmup, and repeat runs
before interpreting small differences. Benchmarks run sequentially within each
Python environment; do not run multiple benchmark sessions concurrently on the
same machine.

Each backend uses its default formatter configuration. The two measurement
layers are:

- **Serialization:** `jsonify_log_record()` on a prepared dictionary, including
  bytes-to-string conversion in the `orjson` and `msgspec` formatters.
- **Formatting:** `format(LogRecord)` on a prepared record, including field
  extraction, message handling, exception formatting where applicable, and
  serialization.

Formatter and record construction, payload preparation, correctness checks, and
handler I/O are outside the timed operation. Formatters and records are reused.
Checks before and after measurement verify expected parsed content and
consistent repeated output. Exception records retain `exc_info`, so formatting
includes rendering the traceback on each call; serialization uses prepared
exception text.

| Workload | Payload |
| --- | --- |
| `simple` | A short string message |
| `structured` | A string message with scalar LogRecord extras |
| `nested` | A dictionary message containing 100 objects with lists and nested metrics |
| `unicode` | A repeated message containing accented text, Japanese text, and emoji |
| `rich` | A dictionary message containing a UTC datetime, UUID, and dataclass |
| `exception` | A message and a prepared ValueError traceback |

Default outputs can differ. Stdlib JSON escapes non-ASCII characters and uses
spaces between elements; the other backends emit compact UTF-8. UTC datetime
strings use `+00:00` for stdlib and orjson, and `Z` for msgspec. These are
comparisons of the supported formatter defaults, including native rich-type
support and fallback encoding costs. They are not byte-identical raw encoder
comparisons. JSON results record each case's output size.

## Interpret and update results

Tables show median microseconds per operation. Speedup is the stdlib median
divided by the backend median for the same workload, layer, and Python version;
values above 1 mean the backend was faster in that measurement. Raw JSON retains
sample statistics, measurement settings, machine information, source revision,
and exact dependency versions. Compare like environments and inspect variability
before claiming a performance change. Hosted runners can use different CPUs and
have variable contention, so cross-version numbers do not isolate interpreter
performance.

The curated baseline consists of one JSON file per Python version under
`benchmarks/results/`, collected from one manual workflow invocation. Later
workflow runs remain artifacts until explicitly selected as a replacement.
Download all six artifacts from the chosen invocation, copy their JSON files to
that directory, and regenerate the tables:

```shell
python scripts/benchmark_report.py benchmarks/results/*.json \
  --update docs/benchmarking.md
```

The generator rejects incomplete or duplicate case matrices. Review the source
revision, dependency versions, measurement settings, and variability before
committing refreshed data. Artifact retention is finite; the committed curated
JSON preserves the measurements used by this page.

## Baseline results

<!-- benchmark-results:start -->

Baseline collection is pending.

<!-- benchmark-results:end -->
