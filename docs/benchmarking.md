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

On CPython, this group installs all three backends. On PyPy, it installs only the
stdlib backend and benchmark tools. Cases for unavailable optional encoders are
reported as skipped. Standard GIL-enabled CPython 3.10–3.15 is the published
comparison matrix; each published CPython result must contain all three backends.

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

You can also use tox with its uv runner:

```shell
uvx --with tox-uv tox -e py315-benchmark
uvx --with tox-uv tox -e pypy312-benchmark
```

Append `-benchmark` to a supported tox runtime name to benchmark that interpreter.
The workflow derives its CPython matrix from tox's default environments, so the
supported versions are maintained in one place. Use `uvx --with tox-uv tox -e benchmark`
to use the default interpreter. Results go to the environment's
`envtmpdir`, such as `.tox/py315-benchmark/tmp/benchmark.json`. Pass pytest options
after `--` to select cases or change measurement settings. For example, use
`-k unicode` to select Unicode workloads. Normal test runs collect only `tests/`
and do not need the benchmark dependencies.

The manual **Benchmark JSON formatters** GitHub Actions workflow runs Linux
x86-64 jobs for Python 3.10–3.15. Each job measures all backends on the same
runner and uploads its JSON results as an artifact. Its job summary contains the
comparison table. Timing differences never fail CI.

## Measurement methodology

The suite uses `pytest-benchmark` for pytest integration, automatic calibration,
statistics, and JSON export. Run on an otherwise idle machine, use warmup, and
repeat runs before interpreting small differences. Benchmarks run sequentially within each
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
values above 1 mean the backend was faster in that measurement. A dash marks an
unavailable backend, such as an optional encoder on PyPy. Raw JSON retains
sample statistics, measurement settings, machine information, source revision,
and exact dependency versions. Compare like environments and inspect variability
before claiming a performance change. Hosted runners can use different CPUs and
have variable contention, so cross-version numbers do not isolate interpreter
performance.

The curated baseline consists of one JSON file per Python version under
`benchmarks/results/`, collected from one workflow invocation. Later
workflow runs remain artifacts until explicitly selected as a replacement.
Download all six artifacts from the chosen invocation into
`benchmark-results/downloaded/`. Keep each JSON file under its original name.
Curate the files and regenerate the tables:

```shell
python scripts/benchmark_report.py benchmark-results/downloaded/*.json \
  --curate benchmarks/results
python scripts/benchmark_report.py benchmarks/results/*.json \
  --update docs/benchmarking.md
```

Curation removes individual timing sample arrays to keep repository files small.
It preserves every summary statistic and records the original file’s SHA-256
hash. Workflow artifacts retain the full samples.

The generator rejects incomplete or duplicate case matrices. Review the source
revision, dependency versions, measurement settings, and variability before
committing refreshed data. Artifact retention is finite; the committed curated
JSON preserves the measurements used by this page.

## Baseline results

These measurements come from [workflow run 39110634914](https://github.com/nhairs-bot/python-json-logger/actions/runs/39110634914).
Each table records its measured source revision, exact dependency versions, and environment.

<!-- benchmark-results:start -->

### CPython 3.10.22

Measured: 2026-10-18T08:15:25.909298+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V74 80-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.904 | 0.272; 7.00× | 0.165; 11.56× |
| serialization | structured | 2.759 | 0.446; 6.19× | 0.369; 7.47× |
| serialization | nested | 76.083 | 17.336; 4.39× | 11.217; 6.78× |
| serialization | unicode | 3.149 | 0.946; 3.33× | 0.912; 3.45× |
| serialization | rich | 10.998 | 0.618; 17.80× | 0.468; 23.49× |
| serialization | exception | 2.452 | 0.364; 6.74× | 0.327; 7.50× |
| formatting | simple | 4.046 | 2.197; 1.84× | 1.989; 2.03× |
| formatting | structured | 5.778 | 3.325; 1.74× | 3.190; 1.81× |
| formatting | nested | 77.597 | 19.570; 3.97× | 13.120; 5.91× |
| formatting | unicode | 5.188 | 3.025; 1.72× | 2.970; 1.75× |
| formatting | rich | 13.340 | 2.979; 4.48× | 2.799; 4.77× |
| formatting | exception | 19.980 | 17.857; 1.12× | 17.556; 1.14× |

### CPython 3.11.17

Measured: 2026-10-18T08:15:31.592684+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; INTEL(R) XEON(R) PLATINUM 8573C.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.917 | 0.262; 7.33× | 0.146; 13.14× |
| serialization | structured | 2.797 | 0.411; 6.81× | 0.331; 8.46× |
| serialization | nested | 93.490 | 17.345; 5.39× | 13.066; 7.16× |
| serialization | unicode | 3.560 | 1.113; 3.20× | 1.152; 3.09× |
| serialization | rich | 11.796 | 0.573; 20.59× | 0.457; 25.83× |
| serialization | exception | 2.523 | 0.333; 7.57× | 0.293; 8.62× |
| formatting | simple | 4.708 | 2.089; 2.25× | 1.834; 2.57× |
| formatting | structured | 7.170 | 3.359; 2.13× | 3.225; 2.22× |
| formatting | nested | 97.373 | 20.234; 4.81× | 15.461; 6.30× |
| formatting | unicode | 6.433 | 3.104; 2.07× | 3.088; 2.08× |
| formatting | rich | 15.285 | 2.917; 5.24× | 2.627; 5.82× |
| formatting | exception | 43.151 | 36.734; 1.17× | 36.591; 1.18× |

### CPython 3.12.3

Measured: 2026-10-18T08:15:21.659968+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; INTEL(R) XEON(R) PLATINUM 8573C.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.575 | 0.235; 6.70× | 0.146; 10.80× |
| serialization | structured | 2.281 | 0.363; 6.28× | 0.301; 7.57× |
| serialization | nested | 61.054 | 14.675; 4.16× | 10.753; 5.68× |
| serialization | unicode | 2.826 | 0.866; 3.26× | 0.947; 2.98× |
| serialization | rich | 7.582 | 0.538; 14.10× | 0.412; 18.40× |
| serialization | exception | 2.056 | 0.303; 6.78× | 0.277; 7.42× |
| formatting | simple | 3.150 | 1.496; 2.11× | 1.340; 2.35× |
| formatting | structured | 4.682 | 2.473; 1.89× | 2.391; 1.96× |
| formatting | nested | 61.437 | 16.197; 3.79× | 12.239; 5.02× |
| formatting | unicode | 4.310 | 2.171; 1.99× | 2.215; 1.95× |
| formatting | rich | 9.685 | 2.099; 4.62× | 1.907; 5.08× |
| formatting | exception | 31.815 | 27.805; 1.14× | 27.581; 1.15× |

### CPython 3.13.16

Measured: 2026-10-18T08:15:25.050587+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.927 | 0.352; 5.48× | 0.192; 10.03× |
| serialization | structured | 2.750 | 0.600; 4.58× | 0.443; 6.20× |
| serialization | nested | 71.083 | 22.562; 3.15× | 14.848; 4.79× |
| serialization | unicode | 3.682 | 1.385; 2.66× | 1.268; 2.90× |
| serialization | rich | 9.287 | 0.831; 11.18× | 0.571; 16.26× |
| serialization | exception | 2.551 | 0.457; 5.58× | 0.367; 6.94× |
| formatting | simple | 3.853 | 2.159; 1.78× | 1.973; 1.95× |
| formatting | structured | 5.570 | 3.306; 1.68× | 3.175; 1.75× |
| formatting | nested | 72.395 | 23.975; 3.02× | 16.410; 4.41× |
| formatting | unicode | 5.700 | 3.396; 1.68× | 3.246; 1.76× |
| formatting | rich | 11.491 | 3.045; 3.77× | 2.765; 4.16× |
| formatting | exception | 78.536 | 73.677; 1.07× | 72.225; 1.09× |

### CPython 3.14.8

Measured: 2026-10-18T08:15:17.678283+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V74 80-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.536 | 0.222; 6.93× | 0.147; 10.43× |
| serialization | structured | 2.072 | 0.380; 5.45× | 0.325; 6.38× |
| serialization | nested | 52.137 | 16.835; 3.10× | 11.607; 4.49× |
| serialization | unicode | 3.009 | 0.950; 3.17× | 0.857; 3.51× |
| serialization | rich | 6.660 | 0.576; 11.56× | 0.421; 15.81× |
| serialization | exception | 1.968 | 0.338; 5.82× | 0.281; 7.00× |
| formatting | simple | 2.879 | 1.619; 1.78× | 1.427; 2.02× |
| formatting | structured | 4.031 | 2.362; 1.71× | 2.200; 1.83× |
| formatting | nested | 53.979 | 17.827; 3.03× | 12.980; 4.16× |
| formatting | unicode | 4.347 | 2.424; 1.79× | 2.301; 1.89× |
| formatting | rich | 8.162 | 2.178; 3.75× | 1.958; 4.17× |
| formatting | exception | 37.926 | 35.312; 1.07× | 35.382; 1.07× |

### CPython 3.15.0

Measured: 2026-10-18T08:15:13.731617+00:00. Revision: `cc23c334a5f68097995128bc3a2b2aaddb20df8f`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V45 96-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.2.1.dev1`.

| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1.153 | 0.190; 6.07× | 0.112; 10.27× |
| serialization | structured | 1.553 | 0.280; 5.54× | 0.223; 6.97× |
| serialization | nested | 30.636 | 10.345; 2.96× | 7.291; 4.20× |
| serialization | unicode | 1.968 | 0.743; 2.65× | 0.721; 2.73× |
| serialization | rich | 4.748 | 0.475; 9.99× | 0.303; 15.66× |
| serialization | exception | 1.536 | 0.233; 6.58× | 0.195; 7.86× |
| formatting | simple | 2.007 | 1.096; 1.83× | 1.036; 1.94× |
| formatting | structured | 2.815 | 1.600; 1.76× | 1.531; 1.84× |
| formatting | nested | 32.279 | 12.940; 2.49× | 8.092; 3.99× |
| formatting | unicode | 2.960 | 1.633; 1.81× | 1.672; 1.77× |
| formatting | rich | 5.628 | 1.516; 3.71× | 1.389; 4.05× |
| formatting | exception | 31.288 | 29.174; 1.07× | 29.265; 1.07× |

<!-- benchmark-results:end -->
