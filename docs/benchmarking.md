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
reported as skipped. The published comparison covers standard
GIL-enabled CPython 3.10–3.15 and PyPy 3.10–3.12. Each published CPython result
must contain all three backends; PyPy results contain stdlib JSON only.

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
The workflow derives its runtime matrix from tox's default environments, so the
supported versions are maintained in one place. Use `uvx --with tox-uv tox -e benchmark`
to use the default interpreter. Results go to the environment's
`envtmpdir`, such as `.tox/py315-benchmark/tmp/benchmark.json`. Pass pytest options
after `--` to select cases or change measurement settings. For example, use
`-k unicode` to select Unicode workloads. Normal test runs collect only `tests/`
and do not need the benchmark dependencies.

The manual **Benchmark JSON formatters** GitHub Actions workflow runs Linux
x86-64 jobs for the supported CPython and PyPy versions. Each job measures
the available backends on the same runner and uploads its JSON results as an artifact. Its job summary contains the
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

## Repetitions, variation, and precision

Warmup and calibration run before timing. `pytest-benchmark` chooses a batch of
iterations per round and repeats those rounds. Statistics describe the
per-operation average duration of each round, rather than individual logging
call latencies. See the [pytest-benchmark glossary](https://pytest-benchmark.readthedocs.io/en/latest/glossary.html).

The generated summary and timing tables record the actual round counts and
iterations per round. Calibration and
warmup calls are additional and are excluded from those counts. Each runtime
has one full suite run; thousands of timing rounds are not thousands of
independent suite runs or machines.

Timing tables show median, arithmetic mean, standard deviation (SD), and
interquartile range (IQR), all in microseconds per operation. IQR is Q3 minus Q1:
the width containing the middle 50% of round averages. Median and IQR are less
sensitive to slow outliers than mean and SD. The JSON also retains minimum,
maximum, quartiles, and outlier counts.

There is no universally trustworthy number of decimal places in microseconds.
The generated summary reports the observed SD relative to the mean, including
outliers. Reported times use at most three significant digits; spreads and speedups use
at most two. This is display rounding, not a claim of accuracy. Batching reduces
timer overhead, but cannot eliminate scheduler, garbage collection, CPU frequency,
or hosted-runner variation. Do not interpret the final displayed digit as a
reliable performance difference. Check IQR and SD, and repeat complete runs on
the same machine before drawing conclusions about small differences.

Time plots use a logarithmic axis to accommodate the different workload sizes.
Points show medians; whiskers span Q1–Q3. These whiskers show within-run spread,
not confidence intervals, and do not measure between-run reproducibility.
Separate speedup tables and plots divide the stdlib median by each backend's
median for the same workload, layer, and Python major/minor version. The
reference is CPython stdlib JSON; a standalone PyPy report uses PyPy stdlib JSON. Values above 1 mean that the
backend was faster in that measurement. Speedups are descriptive ratios without
inferred confidence intervals. Only stdlib JSON is measured on PyPy. Hosted jobs can use different hardware,
so comparisons between implementations or versions do not isolate interpreter
performance. Exact patch versions and environments are recorded separately.

## Update results

The curated baseline consists of one JSON file per Python implementation and version under
`benchmarks/results/`, collected from one workflow invocation. Later
workflow runs remain artifacts until explicitly selected as a replacement.
Download all runtime artifacts from the chosen invocation into
`benchmark-results/downloaded/`. Keep each JSON file under its original name.
Curate the files and regenerate the tables:

```shell
python scripts/benchmark_report.py benchmark-results/downloaded/*.json \
  --curate benchmarks/results
python scripts/benchmark_report.py benchmarks/results/*.json \
  --update docs/benchmarking.md --plots assets/benchmarking
uv run --no-default-groups --group benchmark-report \
  python scripts/benchmark_plots.py benchmarks/results/*.json \
  --output docs/assets/benchmarking
```

Curation removes individual timing sample arrays to keep repository files small.
It preserves every summary statistic and records the original file’s SHA-256
hash. Workflow artifacts retain the full samples.

Plot generation uses Matplotlib in the separate `benchmark-report` dependency
group; it adds no dependency to timed benchmark runs or ordinary tests. The SVG
files contain text labels and can be exported or shared separately. Both plot
types are generated from the same committed summaries as the tables.

The generator rejects incomplete or duplicate case matrices. Review the source
revision, dependency versions, measurement settings, and variability before
committing refreshed data. Artifact retention is finite; the committed curated
JSON preserves the measurements used by this page.

## Baseline results

These measurements come from [workflow run 40178087913](https://github.com/nhairs-bot/python-json-logger/actions/runs/40178087913).
Each table records its measured source revision, exact dependency versions, and environment.
Some PyPy rounds take milliseconds despite microsecond medians; these outliers
are retained and can make SD exceed the mean. These measurements do not identify
the cause of the pauses.

<!-- benchmark-results:start -->

Observed repetitions: 7,536–199,641 rounds per case, with 1–100 iterations per round. Warmup and calibration calls are additional.

Within-run SD/mean: 4.8%–4.8e+02% across cases, including outliers. This does not measure between-run variation.

### Python 3.10

**CPython 3.10.22**. Measured: 2026-10-25T08:50:17.594989+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

**PyPy 3.10.16**. Measured: 2026-10-25T08:49:22.989582+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor. PyPy release: 7.3.19.

Dependencies: `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.10](assets/benchmarking/python-3.10-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 2.48 | 0.033 | 2.51 ± 0.21 | 41,817 × 10 |
| serialization | simple | orjson (CPython) | 0.43 | 0.0062 | 0.437 ± 0.07 | 185,874 × 13 |
| serialization | simple | msgspec (CPython) | 0.235 | 0.0022 | 0.237 ± 0.018 | 44,009 × 100 |
| serialization | simple | json (PyPy) | 0.373 | 0.011 | 0.39 ± 0.11 | 194,175 × 15 |
| serialization | structured | json (CPython) | 3.47 | 0.065 | 3.53 ± 0.57 | 151,930 × 2 |
| serialization | structured | orjson (CPython) | 0.645 | 0.011 | 0.661 ± 0.12 | 159,975 × 10 |
| serialization | structured | msgspec (CPython) | 0.473 | 0.0091 | 0.479 ± 0.069 | 183,824 × 12 |
| serialization | structured | json (PyPy) | 1.01 | 0.019 | 1.09 ± 0.32 | 103,649 × 10 |
| serialization | nested | json (CPython) | 99.7 | 0.91 | 101 ± 5 | 10,173 × 1 |
| serialization | nested | orjson (CPython) | 22.2 | 0.16 | 22.5 ± 1.8 | 44,739 × 1 |
| serialization | nested | msgspec (CPython) | 15.7 | 0.17 | 16 ± 1.5 | 74,823 × 1 |
| serialization | nested | json (PyPy) | 59.1 | 1.6 | 64.2 ± 1.3e+02 | 17,453 × 1 |
| serialization | unicode | json (CPython) | 4.05 | 0.065 | 4.12 ± 0.63 | 128,634 × 2 |
| serialization | unicode | orjson (CPython) | 1.41 | 0.012 | 1.43 ± 0.17 | 72,125 × 10 |
| serialization | unicode | msgspec (CPython) | 1.25 | 0.012 | 1.26 ± 0.13 | 83,251 × 10 |
| serialization | unicode | json (PyPy) | 1.88 | 0.021 | 1.96 ± 0.32 | 54,482 × 10 |
| serialization | rich | json (CPython) | 14.9 | 0.21 | 15.3 ± 2.3 | 69,267 × 1 |
| serialization | rich | orjson (CPython) | 0.858 | 0.01 | 0.869 ± 0.11 | 119,261 × 10 |
| serialization | rich | msgspec (CPython) | 0.611 | 0.01 | 0.621 ± 0.094 | 167,729 × 10 |
| serialization | rich | json (PyPy) | 10.6 | 0.18 | 11 ± 2.3 | 100,716 × 1 |
| serialization | exception | json (CPython) | 3.23 | 0.06 | 3.29 ± 0.5 | 160,231 × 2 |
| serialization | exception | orjson (CPython) | 0.554 | 0.012 | 0.567 ± 0.11 | 190,115 × 10 |
| serialization | exception | msgspec (CPython) | 0.458 | 0.0092 | 0.465 ± 0.079 | 191,571 × 12 |
| serialization | exception | json (PyPy) | 0.985 | 0.015 | 1.03 ± 3.2 | 105,742 × 10 |
| formatting | simple | json (CPython) | 5.04 | 0.075 | 5.13 ± 0.68 | 102,797 × 2 |
| formatting | simple | orjson (CPython) | 2.88 | 0.051 | 2.93 ± 0.49 | 182,816 × 2 |
| formatting | simple | msgspec (CPython) | 2.63 | 0.045 | 2.67 ± 0.45 | 198,060 × 2 |
| formatting | simple | json (PyPy) | 2.64 | 0.05 | 2.78 ± 12 | 196,890 × 2 |
| formatting | structured | json (CPython) | 7.43 | 0.13 | 7.59 ± 1.3 | 139,218 × 1 |
| formatting | structured | orjson (CPython) | 4.4 | 0.065 | 4.47 ± 0.6 | 116,064 × 2 |
| formatting | structured | msgspec (CPython) | 4.16 | 0.06 | 4.3 ± 1.8 | 123,993 × 2 |
| formatting | structured | json (PyPy) | 4.21 | 0.055 | 4.35 ± 2.8 | 122,459 × 2 |
| formatting | nested | json (CPython) | 102 | 1.2 | 103 ± 5 | 10,010 × 1 |
| formatting | nested | orjson (CPython) | 25 | 0.19 | 25.4 ± 2.3 | 40,168 × 1 |
| formatting | nested | msgspec (CPython) | 16.4 | 0.18 | 16.7 ± 1.7 | 62,540 × 1 |
| formatting | nested | json (PyPy) | 63.8 | 4 | 69.3 ± 1.2e+02 | 16,531 × 1 |
| formatting | unicode | json (CPython) | 6.69 | 0.11 | 6.82 ± 1.1 | 155,232 × 1 |
| formatting | unicode | orjson (CPython) | 4.04 | 0.06 | 4.11 ± 0.64 | 128,618 × 2 |
| formatting | unicode | msgspec (CPython) | 3.76 | 0.046 | 3.82 ± 0.56 | 136,538 × 2 |
| formatting | unicode | json (PyPy) | 4.28 | 0.075 | 4.54 ± 22 | 120,715 × 2 |
| formatting | rich | json (CPython) | 19 | 0.65 | 19.9 ± 4.9 | 54,544 × 1 |
| formatting | rich | orjson (CPython) | 3.92 | 0.056 | 3.98 ± 0.57 | 133,281 × 2 |
| formatting | rich | msgspec (CPython) | 3.57 | 0.056 | 3.62 ± 0.53 | 144,865 × 2 |
| formatting | rich | json (PyPy) | 15.8 | 0.29 | 16.6 ± 3.7 | 66,278 × 1 |
| formatting | exception | json (CPython) | 38.1 | 0.84 | 39.2 ± 4.4 | 27,881 × 1 |
| formatting | exception | orjson (CPython) | 32.9 | 0.76 | 34 ± 4.5 | 32,147 × 1 |
| formatting | exception | msgspec (CPython) | 33 | 0.9 | 34 ± 4 | 32,262 × 1 |
| formatting | exception | json (PyPy) | 9.52 | 0.15 | 10.7 ± 49 | 108,378 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.10](assets/benchmarking/python-3.10-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) | json (PyPy) |
| --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | 1× | 5.8× | 11× | 6.6× |
| serialization | structured | 1× | 5.4× | 7.3× | 3.4× |
| serialization | nested | 1× | 4.5× | 6.3× | 1.7× |
| serialization | unicode | 1× | 2.9× | 3.2× | 2.2× |
| serialization | rich | 1× | 17× | 24× | 1.4× |
| serialization | exception | 1× | 5.8× | 7.1× | 3.3× |
| formatting | simple | 1× | 1.8× | 1.9× | 1.9× |
| formatting | structured | 1× | 1.7× | 1.8× | 1.8× |
| formatting | nested | 1× | 4.1× | 6.2× | 1.6× |
| formatting | unicode | 1× | 1.7× | 1.8× | 1.6× |
| formatting | rich | 1× | 4.8× | 5.3× | 1.2× |
| formatting | exception | 1× | 1.2× | 1.2× | 4× |

### Python 3.11

**CPython 3.11.17**. Measured: 2026-10-25T08:51:01.183076+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

**PyPy 3.11.17**. Measured: 2026-10-25T08:49:18.141526+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V45 96-Core Processor. PyPy release: 8.0.1.

Dependencies: `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.11](assets/benchmarking/python-3.11-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 2.02 | 0.035 | 2.06 ± 0.23 | 50,462 × 10 |
| serialization | simple | orjson (CPython) | 0.362 | 0.0067 | 0.369 ± 0.059 | 198,847 × 15 |
| serialization | simple | msgspec (CPython) | 0.172 | 0.0039 | 0.178 ± 0.032 | 59,446 × 100 |
| serialization | simple | json (PyPy) | 0.244 | 0.0066 | 0.248 ± 0.039 | 43,244 × 100 |
| serialization | structured | json (CPython) | 3.14 | 0.066 | 3.25 ± 0.69 | 170,911 × 2 |
| serialization | structured | orjson (CPython) | 0.58 | 0.013 | 0.589 ± 0.096 | 182,150 × 10 |
| serialization | structured | msgspec (CPython) | 0.412 | 0.0069 | 0.421 ± 0.073 | 191,571 × 13 |
| serialization | structured | json (PyPy) | 0.825 | 0.0061 | 0.843 ± 2.2 | 121,774 × 10 |
| serialization | nested | json (CPython) | 106 | 2.2 | 108 ± 6.4 | 9,672 × 1 |
| serialization | nested | orjson (CPython) | 21.9 | 0.2 | 22.7 ± 4.7 | 46,534 × 1 |
| serialization | nested | msgspec (CPython) | 14.1 | 0.2 | 14.4 ± 1.7 | 74,600 × 1 |
| serialization | nested | json (PyPy) | 65.2 | 1.1 | 69 ± 98 | 15,730 × 1 |
| serialization | unicode | json (CPython) | 3.73 | 0.06 | 3.81 ± 0.65 | 139,802 × 2 |
| serialization | unicode | orjson (CPython) | 1.33 | 0.0093 | 1.35 ± 0.16 | 76,605 × 10 |
| serialization | unicode | msgspec (CPython) | 1.19 | 0.0079 | 1.21 ± 0.15 | 84,460 × 10 |
| serialization | unicode | json (PyPy) | 1.07 | 0.018 | 1.09 ± 0.12 | 97,324 × 10 |
| serialization | rich | json (CPython) | 11.8 | 0.28 | 12.1 ± 1.9 | 91,660 × 1 |
| serialization | rich | orjson (CPython) | 0.847 | 0.012 | 0.86 ± 0.12 | 124,922 × 10 |
| serialization | rich | msgspec (CPython) | 0.592 | 0.009 | 0.6 ± 0.087 | 176,026 × 10 |
| serialization | rich | json (PyPy) | 6.07 | 0.19 | 6.44 ± 17 | 172,177 × 1 |
| serialization | exception | json (CPython) | 2.8 | 0.065 | 2.85 ± 0.49 | 187,653 × 2 |
| serialization | exception | orjson (CPython) | 0.464 | 0.0067 | 0.471 ± 0.072 | 186,220 × 12 |
| serialization | exception | msgspec (CPython) | 0.355 | 0.0061 | 0.359 ± 0.056 | 194,553 × 15 |
| serialization | exception | json (PyPy) | 0.572 | 0.026 | 0.593 ± 1.5 | 182,516 × 10 |
| formatting | simple | json (CPython) | 4.09 | 0.1 | 4.19 ± 0.78 | 130,481 × 2 |
| formatting | simple | orjson (CPython) | 2.2 | 0.041 | 2.23 ± 0.2 | 47,688 × 10 |
| formatting | simple | msgspec (CPython) | 2.03 | 0.033 | 2.06 ± 0.19 | 52,043 × 10 |
| formatting | simple | json (PyPy) | 1.57 | 0.046 | 1.63 ± 4.8 | 66,446 × 10 |
| formatting | structured | json (CPython) | 6.11 | 0.15 | 6.26 ± 1.3 | 171,204 × 1 |
| formatting | structured | orjson (CPython) | 3.55 | 0.076 | 3.61 ± 0.57 | 146,135 × 2 |
| formatting | structured | msgspec (CPython) | 3.3 | 0.075 | 3.35 ± 0.53 | 158,958 × 2 |
| formatting | structured | json (PyPy) | 2.59 | 0.045 | 2.69 ± 7.9 | 198,492 × 2 |
| formatting | nested | json (CPython) | 108 | 2.3 | 111 ± 8.3 | 9,454 × 1 |
| formatting | nested | orjson (CPython) | 24 | 0.26 | 24.4 ± 2.2 | 42,512 × 1 |
| formatting | nested | msgspec (CPython) | 16.4 | 0.24 | 16.7 ± 1.8 | 63,780 × 1 |
| formatting | nested | json (PyPy) | 67.4 | 2.4 | 68.1 ± 14 | 15,284 × 1 |
| formatting | unicode | json (CPython) | 5.83 | 0.12 | 5.95 ± 1.1 | 181,489 × 1 |
| formatting | unicode | orjson (CPython) | 3.39 | 0.066 | 3.49 ± 10 | 156,691 × 2 |
| formatting | unicode | msgspec (CPython) | 3.2 | 0.06 | 3.24 ± 0.52 | 164,990 × 2 |
| formatting | unicode | json (PyPy) | 2.36 | 0.039 | 2.4 ± 0.15 | 43,602 × 10 |
| formatting | rich | json (CPython) | 14.5 | 0.38 | 15 ± 2.3 | 73,282 × 1 |
| formatting | rich | orjson (CPython) | 3.16 | 0.075 | 3.2 ± 0.47 | 169,177 × 2 |
| formatting | rich | msgspec (CPython) | 2.85 | 0.07 | 2.93 ± 0.82 | 188,680 × 2 |
| formatting | rich | json (PyPy) | 8.55 | 0.1 | 8.92 ± 34 | 122,235 × 1 |
| formatting | exception | json (CPython) | 49.5 | 1.4 | 51.5 ± 6.1 | 20,992 × 1 |
| formatting | exception | orjson (CPython) | 43.8 | 1.4 | 45.7 ± 6.1 | 24,040 × 1 |
| formatting | exception | msgspec (CPython) | 44.1 | 1.4 | 45.9 ± 5.9 | 23,926 × 1 |
| formatting | exception | json (PyPy) | 11.7 | 0.13 | 12.3 ± 25 | 86,972 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.11](assets/benchmarking/python-3.11-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) | json (PyPy) |
| --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | 1× | 5.6× | 12× | 8.3× |
| serialization | structured | 1× | 5.4× | 7.6× | 3.8× |
| serialization | nested | 1× | 4.8× | 7.5× | 1.6× |
| serialization | unicode | 1× | 2.8× | 3.1× | 3.5× |
| serialization | rich | 1× | 14× | 20× | 1.9× |
| serialization | exception | 1× | 6× | 7.9× | 4.9× |
| formatting | simple | 1× | 1.9× | 2× | 2.6× |
| formatting | structured | 1× | 1.7× | 1.9× | 2.4× |
| formatting | nested | 1× | 4.5× | 6.6× | 1.6× |
| formatting | unicode | 1× | 1.7× | 1.8× | 2.5× |
| formatting | rich | 1× | 4.6× | 5.1× | 1.7× |
| formatting | exception | 1× | 1.1× | 1.1× | 4.2× |

### Python 3.12

**CPython 3.12.3**. Measured: 2026-10-25T08:50:00.599430+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V45 96-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

**PyPy 3.12.15**. Measured: 2026-10-25T08:49:22.839684+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor. PyPy release: 8.0.1.

Dependencies: `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.12](assets/benchmarking/python-3.12-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 1.41 | 0.023 | 1.42 ± 0.095 | 73,363 × 10 |
| serialization | simple | orjson (CPython) | 0.171 | 0.0037 | 0.172 ± 0.013 | 61,943 × 100 |
| serialization | simple | msgspec (CPython) | 0.0973 | 0.0021 | 0.102 ± 0.046 | 101,575 × 100 |
| serialization | simple | json (PyPy) | 0.54 | 0.008 | 0.561 ± 2.2 | 191,939 × 10 |
| serialization | structured | json (CPython) | 1.86 | 0.017 | 1.88 ± 0.14 | 55,596 × 10 |
| serialization | structured | orjson (CPython) | 0.293 | 0.0056 | 0.296 ± 0.037 | 195,428 × 18 |
| serialization | structured | msgspec (CPython) | 0.222 | 0.012 | 0.223 ± 0.022 | 47,889 × 100 |
| serialization | structured | json (PyPy) | 1.44 | 0.014 | 1.47 ± 0.21 | 70,943 × 10 |
| serialization | nested | json (CPython) | 41.8 | 0.75 | 42.7 ± 3.9 | 24,906 × 1 |
| serialization | nested | orjson (CPython) | 10.2 | 0.36 | 10.3 ± 0.78 | 103,264 × 1 |
| serialization | nested | msgspec (CPython) | 6.86 | 0.19 | 7.1 ± 2.7 | 153,398 × 1 |
| serialization | nested | json (PyPy) | 132 | 1.8 | 134 ± 6.6 | 7,667 × 1 |
| serialization | unicode | json (CPython) | 2.19 | 0.032 | 2.23 ± 0.21 | 46,441 × 10 |
| serialization | unicode | orjson (CPython) | 0.669 | 0.017 | 0.706 ± 0.36 | 159,262 × 10 |
| serialization | unicode | msgspec (CPython) | 0.661 | 0.02 | 0.683 ± 0.31 | 160,283 × 10 |
| serialization | unicode | json (PyPy) | 2.34 | 0.021 | 2.39 ± 0.22 | 43,625 × 10 |
| serialization | rich | json (CPython) | 5.57 | 0.11 | 5.69 ± 2 | 185,254 × 1 |
| serialization | rich | orjson (CPython) | 0.501 | 0.011 | 0.516 ± 0.24 | 185,598 × 11 |
| serialization | rich | msgspec (CPython) | 0.281 | 0.0053 | 0.288 ± 0.13 | 192,050 × 19 |
| serialization | rich | json (PyPy) | 12 | 0.17 | 12.4 ± 2.3 | 87,093 × 1 |
| serialization | exception | json (CPython) | 1.7 | 0.018 | 1.73 ± 0.41 | 59,899 × 10 |
| serialization | exception | orjson (CPython) | 0.229 | 0.006 | 0.232 ± 0.034 | 45,740 × 100 |
| serialization | exception | msgspec (CPython) | 0.186 | 0.0045 | 0.187 ± 0.018 | 54,295 × 100 |
| serialization | exception | json (PyPy) | 1.31 | 0.02 | 1.3 ± 0.18 | 89,687 × 10 |
| formatting | simple | json (CPython) | 2.37 | 0.07 | 2.38 ± 0.16 | 44,536 × 10 |
| formatting | simple | orjson (CPython) | 1.18 | 0.028 | 1.2 ± 0.2 | 85,933 × 10 |
| formatting | simple | msgspec (CPython) | 1.09 | 0.019 | 1.12 ± 0.46 | 96,666 × 10 |
| formatting | simple | json (PyPy) | 3.12 | 0.04 | 3.26 ± 12 | 165,262 × 2 |
| formatting | structured | json (CPython) | 3.46 | 0.05 | 3.49 ± 0.35 | 149,032 × 2 |
| formatting | structured | orjson (CPython) | 1.96 | 0.045 | 1.98 ± 0.16 | 51,656 × 10 |
| formatting | structured | msgspec (CPython) | 1.95 | 0.03 | 1.97 ± 0.16 | 52,277 × 10 |
| formatting | structured | json (PyPy) | 5.08 | 0.055 | 5.37 ± 23 | 100,513 × 2 |
| formatting | nested | json (CPython) | 42.2 | 0.61 | 42.7 ± 4.1 | 24,563 × 1 |
| formatting | nested | orjson (CPython) | 11.4 | 0.2 | 11.6 ± 2.6 | 90,196 × 1 |
| formatting | nested | msgspec (CPython) | 7.96 | 0.13 | 8.12 ± 1.7 | 132,083 × 1 |
| formatting | nested | json (PyPy) | 136 | 5 | 141 ± 41 | 7,536 × 1 |
| formatting | unicode | json (CPython) | 3.22 | 0.045 | 3.26 ± 0.36 | 161,577 × 2 |
| formatting | unicode | orjson (CPython) | 1.79 | 0.027 | 1.82 ± 0.32 | 56,603 × 10 |
| formatting | unicode | msgspec (CPython) | 1.72 | 0.027 | 1.74 ± 0.1 | 60,296 × 10 |
| formatting | unicode | json (PyPy) | 5.01 | 0.06 | 5.13 ± 0.78 | 102,902 × 2 |
| formatting | rich | json (CPython) | 6.81 | 0.14 | 7.08 ± 3 | 154,560 × 1 |
| formatting | rich | orjson (CPython) | 1.68 | 0.03 | 1.7 ± 0.1 | 60,115 × 10 |
| formatting | rich | msgspec (CPython) | 1.54 | 0.021 | 1.59 ± 0.47 | 66,393 × 10 |
| formatting | rich | json (PyPy) | 18 | 0.24 | 18.9 ± 35 | 58,337 × 1 |
| formatting | exception | json (CPython) | 18.5 | 0.64 | 19.1 ± 4.9 | 57,320 × 1 |
| formatting | exception | orjson (CPython) | 16.6 | 0.28 | 17 ± 3.1 | 62,799 × 1 |
| formatting | exception | msgspec (CPython) | 16.3 | 0.35 | 16.5 ± 1.5 | 62,838 × 1 |
| formatting | exception | json (PyPy) | 29.6 | 0.65 | 33.9 ± 1e+02 | 35,035 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.12](assets/benchmarking/python-3.12-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) | json (PyPy) |
| --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | 1× | 8.3× | 14× | 2.6× |
| serialization | structured | 1× | 6.3× | 8.4× | 1.3× |
| serialization | nested | 1× | 4.1× | 6.1× | 0.32× |
| serialization | unicode | 1× | 3.3× | 3.3× | 0.93× |
| serialization | rich | 1× | 11× | 20× | 0.46× |
| serialization | exception | 1× | 7.4× | 9.2× | 1.3× |
| formatting | simple | 1× | 2× | 2.2× | 0.76× |
| formatting | structured | 1× | 1.8× | 1.8× | 0.68× |
| formatting | nested | 1× | 3.7× | 5.3× | 0.31× |
| formatting | unicode | 1× | 1.8× | 1.9× | 0.64× |
| formatting | rich | 1× | 4.1× | 4.4× | 0.38× |
| formatting | exception | 1× | 1.1× | 1.1× | 0.63× |

### Python 3.13

**CPython 3.13.17**. Measured: 2026-10-25T08:50:12.277781+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.13](assets/benchmarking/python-3.13-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 1.93 | 0.02 | 1.96 ± 0.16 | 52,925 × 10 |
| serialization | simple | orjson (CPython) | 0.338 | 0.0051 | 0.344 ± 0.055 | 191,939 × 16 |
| serialization | simple | msgspec (CPython) | 0.198 | 0.0036 | 0.2 ± 0.015 | 52,395 × 100 |
| serialization | structured | json (CPython) | 2.71 | 0.045 | 2.78 ± 0.56 | 190,115 × 2 |
| serialization | structured | orjson (CPython) | 0.558 | 0.01 | 0.566 ± 0.081 | 187,266 × 10 |
| serialization | structured | msgspec (CPython) | 0.412 | 0.0069 | 0.417 ± 0.061 | 194,553 × 13 |
| serialization | nested | json (CPython) | 70 | 0.74 | 71.2 ± 3.7 | 14,339 × 1 |
| serialization | nested | orjson (CPython) | 22.4 | 0.17 | 22.8 ± 2.1 | 45,307 × 1 |
| serialization | nested | msgspec (CPython) | 15.1 | 0.29 | 15.3 ± 1.4 | 70,092 × 1 |
| serialization | unicode | json (CPython) | 3.65 | 0.045 | 3.79 ± 0.78 | 139,782 × 2 |
| serialization | unicode | orjson (CPython) | 1.37 | 0.015 | 1.39 ± 0.15 | 74,600 × 10 |
| serialization | unicode | msgspec (CPython) | 1.29 | 0.007 | 1.3 ± 0.14 | 79,277 × 10 |
| serialization | rich | json (CPython) | 9.05 | 0.14 | 9.25 ± 1.5 | 114,208 × 1 |
| serialization | rich | orjson (CPython) | 0.798 | 0.011 | 0.81 ± 0.1 | 129,283 × 10 |
| serialization | rich | msgspec (CPython) | 0.58 | 0.009 | 0.586 ± 0.076 | 178,891 × 10 |
| serialization | exception | json (CPython) | 2.59 | 0.044 | 2.63 ± 0.43 | 198,060 × 2 |
| serialization | exception | orjson (CPython) | 0.447 | 0.0058 | 0.453 ± 0.071 | 190,477 × 12 |
| serialization | exception | msgspec (CPython) | 0.369 | 0.0067 | 0.373 ± 0.052 | 187,266 × 15 |
| formatting | simple | json (CPython) | 3.83 | 0.086 | 3.9 ± 0.57 | 136,725 × 2 |
| formatting | simple | orjson (CPython) | 2.18 | 0.048 | 2.21 ± 0.19 | 48,335 × 10 |
| formatting | simple | msgspec (CPython) | 2 | 0.044 | 2.02 ± 0.17 | 52,646 × 10 |
| formatting | structured | json (CPython) | 5.57 | 0.14 | 5.68 ± 1 | 188,680 × 1 |
| formatting | structured | orjson (CPython) | 3.38 | 0.095 | 3.44 ± 0.52 | 159,949 × 2 |
| formatting | structured | msgspec (CPython) | 3.18 | 0.09 | 3.22 ± 0.49 | 169,751 × 2 |
| formatting | nested | json (CPython) | 70.8 | 0.83 | 72.3 ± 6 | 14,227 × 1 |
| formatting | nested | orjson (CPython) | 24 | 0.2 | 24.4 ± 2 | 42,295 × 1 |
| formatting | nested | msgspec (CPython) | 16.5 | 0.19 | 16.8 ± 1.8 | 62,228 × 1 |
| formatting | unicode | json (CPython) | 5.58 | 0.1 | 5.67 ± 1 | 185,529 × 1 |
| formatting | unicode | orjson (CPython) | 3.3 | 0.065 | 3.36 ± 0.53 | 161,499 × 2 |
| formatting | unicode | msgspec (CPython) | 3.22 | 0.06 | 3.27 ± 0.53 | 166,086 × 2 |
| formatting | rich | json (CPython) | 11.3 | 0.19 | 11.6 ± 1.9 | 92,337 × 1 |
| formatting | rich | orjson (CPython) | 3.03 | 0.07 | 3.07 ± 0.47 | 176,026 × 2 |
| formatting | rich | msgspec (CPython) | 2.77 | 0.065 | 2.81 ± 0.45 | 192,345 × 2 |
| formatting | exception | json (CPython) | 77 | 2.3 | 80.5 ± 9.2 | 13,378 × 1 |
| formatting | exception | orjson (CPython) | 71.9 | 1.7 | 75 ± 8.5 | 14,282 × 1 |
| formatting | exception | msgspec (CPython) | 71.9 | 2.5 | 75.2 ± 8.9 | 14,389 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.13](assets/benchmarking/python-3.13-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1× | 5.7× | 9.8× |
| serialization | structured | 1× | 4.9× | 6.6× |
| serialization | nested | 1× | 3.1× | 4.6× |
| serialization | unicode | 1× | 2.7× | 2.8× |
| serialization | rich | 1× | 11× | 16× |
| serialization | exception | 1× | 5.8× | 7× |
| formatting | simple | 1× | 1.8× | 1.9× |
| formatting | structured | 1× | 1.6× | 1.8× |
| formatting | nested | 1× | 2.9× | 4.3× |
| formatting | unicode | 1× | 1.7× | 1.7× |
| formatting | rich | 1× | 3.7× | 4.1× |
| formatting | exception | 1× | 1.1× | 1.1× |

### Python 3.14

**CPython 3.14.9**. Measured: 2026-10-25T08:50:12.665132+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 7763 64-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.14](assets/benchmarking/python-3.14-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 1.96 | 0.019 | 1.99 ± 0.21 | 52,643 × 10 |
| serialization | simple | orjson (CPython) | 0.369 | 0.0064 | 0.38 ± 0.085 | 199,641 × 14 |
| serialization | simple | msgspec (CPython) | 0.208 | 0.0025 | 0.211 ± 0.02 | 49,641 × 100 |
| serialization | structured | json (CPython) | 2.74 | 0.04 | 2.8 ± 0.56 | 188,324 × 2 |
| serialization | structured | orjson (CPython) | 0.549 | 0.007 | 0.559 ± 0.1 | 185,529 × 10 |
| serialization | structured | msgspec (CPython) | 0.411 | 0.0046 | 0.418 ± 0.071 | 193,051 × 13 |
| serialization | nested | json (CPython) | 70.4 | 0.45 | 71.6 ± 4.4 | 14,546 × 1 |
| serialization | nested | orjson (CPython) | 22.1 | 0.19 | 22.5 ± 2 | 45,978 × 1 |
| serialization | nested | msgspec (CPython) | 14.4 | 0.18 | 14.8 ± 2.3 | 71,654 × 1 |
| serialization | unicode | json (CPython) | 3.55 | 0.031 | 3.61 ± 0.59 | 143,617 × 2 |
| serialization | unicode | orjson (CPython) | 1.33 | 0.0091 | 1.35 ± 0.18 | 77,078 × 10 |
| serialization | unicode | msgspec (CPython) | 1.2 | 0.008 | 1.22 ± 0.14 | 84,232 × 10 |
| serialization | rich | json (CPython) | 8.69 | 0.11 | 8.91 ± 1.5 | 118,540 × 1 |
| serialization | rich | orjson (CPython) | 0.778 | 0.009 | 0.79 ± 0.11 | 131,165 × 10 |
| serialization | rich | msgspec (CPython) | 0.569 | 0.008 | 0.579 ± 0.089 | 181,489 × 10 |
| serialization | exception | json (CPython) | 2.56 | 0.024 | 2.6 ± 0.36 | 133,977 × 3 |
| serialization | exception | orjson (CPython) | 0.449 | 0.0058 | 0.456 ± 0.065 | 189,754 × 12 |
| serialization | exception | msgspec (CPython) | 0.368 | 0.0044 | 0.373 ± 0.053 | 198,453 × 14 |
| formatting | simple | json (CPython) | 3.68 | 0.055 | 3.75 ± 0.57 | 141,985 × 2 |
| formatting | simple | orjson (CPython) | 1.99 | 0.018 | 2.02 ± 0.17 | 51,664 × 10 |
| formatting | simple | msgspec (CPython) | 1.8 | 0.018 | 1.82 ± 0.16 | 57,399 × 10 |
| formatting | structured | json (CPython) | 5.35 | 0.1 | 5.46 ± 1 | 193,051 × 1 |
| formatting | structured | orjson (CPython) | 3 | 0.05 | 3.05 ± 0.47 | 172,981 × 2 |
| formatting | structured | msgspec (CPython) | 2.8 | 0.045 | 2.84 ± 0.43 | 182,482 × 2 |
| formatting | nested | json (CPython) | 72.8 | 0.67 | 74.3 ± 6.4 | 13,958 × 1 |
| formatting | nested | orjson (CPython) | 23.9 | 0.22 | 24.3 ± 2.3 | 41,835 × 1 |
| formatting | nested | msgspec (CPython) | 16 | 0.17 | 16.3 ± 1.6 | 63,862 × 1 |
| formatting | unicode | json (CPython) | 5.38 | 0.071 | 5.49 ± 0.98 | 191,976 × 1 |
| formatting | unicode | orjson (CPython) | 3.16 | 0.04 | 3.25 ± 12 | 163,106 × 2 |
| formatting | unicode | msgspec (CPython) | 3.02 | 0.03 | 3.06 ± 0.46 | 172,088 × 2 |
| formatting | rich | json (CPython) | 11 | 0.17 | 11.4 ± 2.2 | 93,897 × 1 |
| formatting | rich | orjson (CPython) | 2.8 | 0.044 | 2.84 ± 0.45 | 185,874 × 2 |
| formatting | rich | msgspec (CPython) | 2.54 | 0.03 | 2.58 ± 0.34 | 134,157 × 3 |
| formatting | exception | json (CPython) | 83.8 | 3.1 | 87.6 ± 9 | 12,445 × 1 |
| formatting | exception | orjson (CPython) | 78.8 | 2.8 | 82.3 ± 8.9 | 13,245 × 1 |
| formatting | exception | msgspec (CPython) | 79 | 2.8 | 82.7 ± 9.8 | 13,165 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.14](assets/benchmarking/python-3.14-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1× | 5.3× | 9.4× |
| serialization | structured | 1× | 5× | 6.7× |
| serialization | nested | 1× | 3.2× | 4.9× |
| serialization | unicode | 1× | 2.7× | 2.9× |
| serialization | rich | 1× | 11× | 15× |
| serialization | exception | 1× | 5.7× | 6.9× |
| formatting | simple | 1× | 1.8× | 2× |
| formatting | structured | 1× | 1.8× | 1.9× |
| formatting | nested | 1× | 3× | 4.5× |
| formatting | unicode | 1× | 1.7× | 1.8× |
| formatting | rich | 1× | 3.9× | 4.3× |
| formatting | exception | 1× | 1.1× | 1.1× |

### Python 3.15

**CPython 3.15.1**. Measured: 2026-10-25T08:50:52.380316+00:00. Revision: `70c2907f5ac43b7b8648b6f080b45918705a6e8d`.

Environment: Linux 6.17.0-1022-azure, x86_64; AMD EPYC 9V74 80-Core Processor.

Dependencies: `msgspec==0.22.0`, `orjson==3.13.0`, `pytest==9.1.1`, `pytest-benchmark==5.3.0`, `python-json-logger==4.3.0.dev1`.

#### Times and variation

![Median times and interquartile ranges for Python 3.15](assets/benchmarking/python-3.15-times.svg)

| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| serialization | simple | json (CPython) | 1.47 | 0.018 | 1.49 ± 0.14 | 70,073 × 10 |
| serialization | simple | orjson (CPython) | 0.213 | 0.0031 | 0.216 ± 0.017 | 47,660 × 100 |
| serialization | simple | msgspec (CPython) | 0.145 | 0.0013 | 0.147 ± 0.013 | 69,731 × 100 |
| serialization | structured | json (CPython) | 2.04 | 0.027 | 2.07 ± 0.18 | 50,687 × 10 |
| serialization | structured | orjson (CPython) | 0.361 | 0.0053 | 0.366 ± 0.045 | 190,187 × 15 |
| serialization | structured | msgspec (CPython) | 0.322 | 0.0071 | 0.331 ± 0.056 | 192,382 × 17 |
| serialization | nested | json (CPython) | 57 | 0.66 | 58 ± 4.3 | 21,478 × 1 |
| serialization | nested | orjson (CPython) | 15.8 | 0.11 | 16 ± 1.2 | 64,380 × 1 |
| serialization | nested | msgspec (CPython) | 12 | 0.18 | 12.1 ± 1.3 | 89,071 × 1 |
| serialization | unicode | json (CPython) | 2.9 | 0.03 | 2.94 ± 0.39 | 177,368 × 2 |
| serialization | unicode | orjson (CPython) | 0.84 | 0.013 | 0.855 ± 0.095 | 120,308 × 10 |
| serialization | unicode | msgspec (CPython) | 0.864 | 0.018 | 0.884 ± 1.1 | 118,864 × 10 |
| serialization | rich | json (CPython) | 6.38 | 0.1 | 6.48 ± 0.76 | 166,141 × 1 |
| serialization | rich | orjson (CPython) | 0.549 | 0.009 | 0.556 ± 0.072 | 189,466 × 10 |
| serialization | rich | msgspec (CPython) | 0.426 | 0.0062 | 0.431 ± 0.049 | 188,041 × 13 |
| serialization | exception | json (CPython) | 1.94 | 0.023 | 1.97 ± 0.16 | 52,524 × 10 |
| serialization | exception | orjson (CPython) | 0.298 | 0.0044 | 0.302 ± 0.035 | 192,382 × 18 |
| serialization | exception | msgspec (CPython) | 0.282 | 0.0037 | 0.286 ± 0.036 | 190,913 × 19 |
| formatting | simple | json (CPython) | 2.92 | 0.055 | 2.97 ± 0.36 | 180,571 × 2 |
| formatting | simple | orjson (CPython) | 1.6 | 0.027 | 1.62 ± 0.12 | 65,561 × 10 |
| formatting | simple | msgspec (CPython) | 1.43 | 0.019 | 1.44 ± 0.11 | 73,041 × 10 |
| formatting | structured | json (CPython) | 4.13 | 0.07 | 4.18 ± 0.42 | 126,551 × 2 |
| formatting | structured | orjson (CPython) | 2.37 | 0.03 | 2.42 ± 0.33 | 43,169 × 10 |
| formatting | structured | msgspec (CPython) | 2.23 | 0.021 | 2.27 ± 0.33 | 46,122 × 10 |
| formatting | nested | json (CPython) | 46.6 | 0.54 | 47.1 ± 2.5 | 21,965 × 1 |
| formatting | nested | orjson (CPython) | 17.3 | 0.13 | 17.5 ± 1.4 | 59,015 × 1 |
| formatting | nested | msgspec (CPython) | 12.9 | 0.12 | 13 ± 0.95 | 79,309 × 1 |
| formatting | unicode | json (CPython) | 4.35 | 0.055 | 4.41 ± 0.42 | 118,316 × 2 |
| formatting | unicode | orjson (CPython) | 2.26 | 0.023 | 2.29 ± 0.14 | 45,470 × 10 |
| formatting | unicode | msgspec (CPython) | 2.22 | 0.027 | 2.26 ± 2.8 | 46,098 × 10 |
| formatting | rich | json (CPython) | 8 | 0.12 | 8.12 ± 0.91 | 130,345 × 1 |
| formatting | rich | orjson (CPython) | 2.14 | 0.022 | 2.16 ± 0.14 | 47,822 × 10 |
| formatting | rich | msgspec (CPython) | 2.17 | 0.026 | 2.2 ± 0.16 | 52,087 × 10 |
| formatting | exception | json (CPython) | 40.6 | 0.95 | 41.6 ± 4.1 | 25,505 × 1 |
| formatting | exception | orjson (CPython) | 37.8 | 0.69 | 38.6 ± 2.9 | 27,409 × 1 |
| formatting | exception | msgspec (CPython) | 37.3 | 0.69 | 38.2 ± 3.7 | 27,342 × 1 |

#### Speedup

![Median speedups relative to stdlib JSON for Python 3.15](assets/benchmarking/python-3.15-speedup.svg)

Reference: json (CPython) (1×).

| Layer | Workload | json (CPython) | orjson (CPython) | msgspec (CPython) |
| --- | --- | ---: | ---: | ---: |
| serialization | simple | 1× | 6.9× | 10× |
| serialization | structured | 1× | 5.6× | 6.3× |
| serialization | nested | 1× | 3.6× | 4.8× |
| serialization | unicode | 1× | 3.4× | 3.4× |
| serialization | rich | 1× | 12× | 15× |
| serialization | exception | 1× | 6.5× | 6.9× |
| formatting | simple | 1× | 1.8× | 2× |
| formatting | structured | 1× | 1.7× | 1.8× |
| formatting | nested | 1× | 2.7× | 3.6× |
| formatting | unicode | 1× | 1.9× | 2× |
| formatting | rich | 1× | 3.7× | 3.7× |
| formatting | exception | 1× | 1.1× | 1.1× |

<!-- benchmark-results:end -->
