"""Generate benchmark tables from pytest-benchmark JSON without extra dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean
from textwrap import indent

START = "<!-- benchmark-results:start -->"
END = "<!-- benchmark-results:end -->"
SUMMARY_START = "<!-- benchmark-summary:start -->"
SUMMARY_END = "<!-- benchmark-summary:end -->"
SERIES = ("json (CPython)", "orjson (CPython)", "msgspec (CPython)", "json (PyPy)")
BACKENDS = ("json", "orjson", "msgspec")
LAYERS = ("serialization", "formatting")
WORKLOADS = ("simple", "structured", "nested", "unicode", "rich", "exception")


def load_results(paths: list[Path]) -> list[dict]:
    """Load summary statistics in deterministic runtime order."""
    results = []
    for path in paths:
        result = json.loads(path.read_text(encoding="utf-8"))
        # Raw exports can contain millions of samples; retain only table inputs.
        for benchmark in result["benchmarks"]:
            benchmark["stats"].pop("data", None)
        results.append(result)
    results.sort(
        key=lambda result: (
            tuple(map(int, result["environment"]["python"].split(".")[:2])),
            result["environment"].get("implementation", "CPython"),
        )
    )
    return results


def comparison_groups(results: list[dict]) -> list[dict]:
    """Validate exports and group implementations by Python major/minor version."""
    groups: dict[str, dict] = {}
    runtimes = set()
    for result in results:
        environment = result["environment"]
        python = environment["python"]
        implementation = environment.get("implementation", "CPython")
        minor = ".".join(python.split(".")[:2])
        runtime = (implementation, minor)
        if implementation not in ("CPython", "PyPy"):
            raise ValueError(f"Unsupported implementation: {implementation}")
        if runtime in runtimes:
            raise ValueError(f"Duplicate runtime: {runtime}")
        runtimes.add(runtime)
        backends = tuple(environment.get("backends", BACKENDS))
        if "json" not in backends or not set(backends).issubset(BACKENDS):
            raise ValueError(f"Invalid backend list for Python {python}")
        cases = {}
        for benchmark in result["benchmarks"]:
            info = benchmark["extra_info"]
            key = (info["layer"], info["workload"], info["backend"])
            if key in cases:
                raise ValueError(f"Duplicate case: {key}")
            median = benchmark["stats"]["median"]
            if not math.isfinite(median) or median <= 0:
                raise ValueError(f"Invalid median: {key}")
            stats = benchmark["stats"]
            for name in ("mean", "stddev", "iqr", "q1", "q3"):
                if not math.isfinite(stats[name]) or stats[name] < 0:
                    raise ValueError(f"Invalid {name}: {key}")
            if stats["mean"] <= 0:
                raise ValueError(f"Invalid mean: {key}")
            if not 0 < stats["q1"] <= median <= stats["q3"]:
                raise ValueError(f"Invalid quartiles: {key}")
            if stats["rounds"] < 1 or stats["iterations"] < 1:
                raise ValueError(f"Invalid repetition counts: {key}")
            cases[key] = stats
        required = {
            (layer, workload, backend)
            for layer in LAYERS
            for workload in WORKLOADS
            for backend in backends
        }
        if set(cases) != required:
            raise ValueError(f"Incomplete or unexpected matrix for Python {python}")
        group = groups.setdefault(
            minor, {"python": minor, "sources": [], "cases": {}, "backends": []}
        )
        group["sources"].append(result)
        for backend in backends:
            label = f"{backend} ({implementation})"
            group["backends"].append(label)
            for layer in LAYERS:
                for workload in WORKLOADS:
                    group["cases"][layer, workload, label] = cases[layer, workload, backend]
    return list(groups.values())


def formatting_summary(groups: list[dict]) -> dict:
    """Aggregate per-version medians and matched CPython-relative ratios.

    Missing CPython references contribute timings but no speedup ratios.
    Each metric retains its own version coverage.
    """
    summary = {}
    for workload in WORKLOADS:
        summary[workload] = {}
        for backend in SERIES:
            metrics = {}
            for kind in ("times", "speedup"):
                values = []
                versions = []
                for group in groups:
                    cases = group["cases"]
                    key = ("formatting", workload, backend)
                    reference = ("formatting", workload, "json (CPython)")
                    if key not in cases or (kind == "speedup" and reference not in cases):
                        continue
                    timing = cases[key]["median"]
                    values.append(
                        timing * 1e6 if kind == "times" else cases[reference]["median"] / timing
                    )
                    versions.append(group["python"])
                if values:
                    metrics[kind] = {
                        "mean": fmean(values),
                        "min": min(values),
                        "max": max(values),
                        "versions": versions,
                    }
            if metrics:
                summary[workload][backend] = metrics
    return summary


def render_summary(groups: list[dict], plots: str | None = None) -> str:
    """Render complete-formatting summaries with explicit version coverage."""
    summary = formatting_summary(groups)
    lines = [
        "## Complete-formatting summary",
        "",
        "Complete formatting includes record processing and serialization. These results use the "
        "[committed baseline](#baseline-results), not application throughput measurements.",
        "",
        "Bars show the arithmetic mean across Python versions of each version's median operation time. "
        "Whiskers show the minimum–maximum across those versions, not individual timing samples "
        "or confidence intervals. Each version has equal weight.",
        "",
        "Speedups are calculated against CPython stdlib JSON for the same workload and Python "
        "major/minor version, then averaged across versions. They are not ratios of "
        "cross-version mean times. Only versions with a matching CPython reference contribute "
        "to speedups. Values above 1× indicate faster formatting.",
        "",
        "Version coverage differs between runtimes, so these summaries do not isolate interpreter "
        "performance. The tables list the versions included in each metric.",
        "",
    ]
    if plots:
        lines += [
            f"![Complete-formatting times and speedups by workload, with mean and version ranges]({plots}/summary.svg)",
            "",
            "Timing panels: lower is faster. Speedup panels: higher is faster; the dashed line marks 1×. "
            "Each panel starts at zero and has its own scale. "
            "Open the SVG to view or share the full-size summary.",
            "",
        ]
    lines += [
        '??? note "Summary values and included versions"',
        "",
        "    | Workload | Encoder | Time mean [min–max] (µs) | Timing versions | Speedup mean [min–max] | Speedup versions |",
        "    | --- | --- | ---: | --- | ---: | --- |",
    ]
    for workload, backends in summary.items():
        for backend, metrics in backends.items():
            cells = []
            for kind in ("times", "speedup"):
                if kind not in metrics:
                    cells.extend(["Unavailable", "None"])
                    continue
                stats = metrics[kind]
                precision = 3 if kind == "times" else 2
                suffix = "" if kind == "times" else "×"
                cells += [
                    f"{stats['mean']:.{precision}g}{suffix} "
                    f"[{stats['min']:.{precision}g}–{stats['max']:.{precision}g}]{suffix}",
                    f"{', '.join(stats['versions'])} (n={len(stats['versions'])})",
                ]
            lines.append(f"    | {workload} | {backend} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def render(paths: list[Path], plots: str | None = None) -> str:
    """Render version sections comparing encoders and Python implementations."""
    results = load_results(paths)
    sections = []
    for group in comparison_groups(results):
        python = group["python"]
        backends = group["backends"]
        cases = group["cases"]
        sections.extend([f"### Python {python}", ""])
        for result in group["sources"]:
            environment = result["environment"]
            implementation = environment.get("implementation", "CPython")
            machine = result["machine_info"]
            cpu = machine.get("cpu", {}).get("brand_raw", machine.get("processor", "unknown"))
            sections.extend(
                [
                    f"**{implementation} {environment['python']}**. Measured: {result['datetime']}. "
                    f"Revision: `{environment['revision']}`"
                    + (" (working tree modified)." if environment["dirty"] else "."),
                    "",
                    f"Environment: {machine['system']} {machine['release']}, {machine['machine']}; {cpu}."
                    + (
                        f" PyPy release: {machine['python_implementation_version']}."
                        if implementation == "PyPy" and "python_implementation_version" in machine
                        else ""
                    ),
                    "",
                    "Dependencies: "
                    + ", ".join(
                        f"`{key}=={value}`"
                        for key, value in sorted(environment["dependencies"].items())
                    )
                    + ".",
                    "",
                ]
            )
        sections.extend(["#### Times and variation", ""])
        slug = f"python-{python}"
        if plots:
            sections.extend(
                [
                    f"![Median operation times for Python {python}]({plots}/{slug}-times.svg)",
                    "",
                ]
            )
        sections.extend(
            [
                "| Layer | Workload | Encoder | Median (µs) | IQR (µs) | Mean ± SD (µs) | Rounds × iterations |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for layer in LAYERS:
            for workload in WORKLOADS:
                for backend in backends:
                    stats = cases[layer, workload, backend]
                    sections.append(
                        f"| {layer} | {workload} | {backend} | "
                        f"{stats['median'] * 1e6:.3g} | {stats['iqr'] * 1e6:.2g} | "
                        f"{stats['mean'] * 1e6:.3g} ± {stats['stddev'] * 1e6:.2g} | "
                        f"{stats['rounds']:,} × {stats['iterations']:,} |"
                    )
        sections.extend(["", "#### Speedup", ""])
        if plots:
            sections.extend(
                [
                    f"![Median speedups relative to stdlib JSON for Python {python}]({plots}/{slug}-speedup.svg)",
                    "",
                ]
            )
        reference = "json (CPython)" if "json (CPython)" in backends else "json (PyPy)"
        sections.extend([f"Reference: {reference} (1×).", ""])
        sections.extend(
            [
                "| Layer | Workload | " + " | ".join(backends) + " |",
                "| --- | --- | " + " | ".join("---:" for _ in backends) + " |",
            ]
        )
        for layer in LAYERS:
            for workload in WORKLOADS:
                baseline = cases[layer, workload, reference]["median"]
                cells = []
                for backend in backends:
                    timing = cases[layer, workload, backend]["median"]
                    cells.append(f"{baseline / timing:.2g}×")
                sections.append(f"| {layer} | {workload} | " + " | ".join(cells) + " |")
        sections.append("")
    statistics = [benchmark["stats"] for result in results for benchmark in result["benchmarks"]]
    rounds = [stats["rounds"] for stats in statistics]
    iterations = [stats["iterations"] for stats in statistics]
    variation = [stats["stddev"] / stats["mean"] * 100 for stats in statistics]
    summary = [
        f"Observed repetitions: {min(rounds):,}–{max(rounds):,} rounds per case, "
        f"with {min(iterations):,}–{max(iterations):,} iterations per round. "
        "Warmup and calibration calls are additional.",
        "",
        f"Within-run SD/mean: {min(variation):.2g}%–{max(variation):.2g}% across cases, "
        "including outliers. This does not measure between-run variation.",
        "",
    ]
    lines = summary + sections
    collapsed = []
    in_table = False
    for line in lines:
        if line.startswith("|"):
            if not in_table:
                title = "Timing statistics" if "Median (µs)" in line else "Speedup values"
                collapsed.extend([f'??? note "{title}"', ""])
            collapsed.append(indent(line, "    "))
            in_table = True
        else:
            collapsed.append(line)
            in_table = False
    return "\n".join(collapsed)


def main() -> None:
    """Print a summary or replace the generated section of a documentation page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--update", type=Path, help="Replace the generated section in this page")
    output.add_argument("--curate", type=Path, help="Save JSON without individual timing samples")
    parser.add_argument("--plots", help="Relative URL prefix for generated SVG plots")
    args = parser.parse_args()
    report = render(args.results, plots=args.plots)
    if args.curate:
        names = [path.name for path in args.results]
        if len(set(names)) != len(names):
            raise ValueError("Curated result filenames must be unique")
        args.curate.mkdir(parents=True, exist_ok=True)
        for path in args.results:
            raw = path.read_bytes()
            result = json.loads(raw)
            for benchmark in result["benchmarks"]:
                benchmark["stats"].pop("data", None)
            result["curation"] = {
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "omitted": ["benchmarks[].stats.data"],
            }
            (args.curate / path.name).write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
    elif args.update:
        text = args.update.read_text(encoding="utf-8")
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before + START + "\n\n" + report + "\n" + END + after
        if SUMMARY_START in text:
            before, rest = text.split(SUMMARY_START, 1)
            _, after = rest.split(SUMMARY_END, 1)
            summary = render_summary(comparison_groups(load_results(args.results)), args.plots)
            text = before + SUMMARY_START + "\n\n" + summary + "\n" + SUMMARY_END + after
        args.update.write_text(text, encoding="utf-8")
    else:
        print(report)
    return


if __name__ == "__main__":
    main()
