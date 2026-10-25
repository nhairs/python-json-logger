"""Generate benchmark tables from pytest-benchmark JSON without extra dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

START = "<!-- benchmark-results:start -->"
END = "<!-- benchmark-results:end -->"
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
                    f"![Median times and interquartile ranges for Python {python}]({plots}/{slug}-times.svg)",
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
    return "\n".join(summary + sections)


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
        args.update.write_text(
            before + START + "\n\n" + report + "\n" + END + after, encoding="utf-8"
        )
    else:
        print(report)
    return


if __name__ == "__main__":
    main()
