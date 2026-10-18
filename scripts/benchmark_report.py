"""Generate benchmark tables from pytest-benchmark JSON without extra dependencies."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

START = "<!-- benchmark-results:start -->"
END = "<!-- benchmark-results:end -->"
BACKENDS = ("json", "orjson", "msgspec")
LAYERS = ("serialization", "formatting")
WORKLOADS = ("simple", "structured", "nested", "unicode", "rich", "exception")


def render(paths: list[Path]) -> str:
    """Render complete per-runtime matrices in deterministic order."""
    results = [json.loads(path.read_text()) for path in paths]
    results.sort(key=lambda result: tuple(map(int, result["environment"]["python"].split("."))))
    sections = []
    runtimes = set()
    for result in results:
        environment = result["environment"]
        python = environment["python"]
        if python in runtimes:
            raise ValueError(f"Duplicate runtime: {python}")
        runtimes.add(python)
        cases = {}
        for benchmark in result["benchmarks"]:
            info = benchmark["extra_info"]
            key = (info["layer"], info["workload"], info["backend"])
            if key in cases:
                raise ValueError(f"Duplicate case: {key}")
            median = benchmark["stats"]["median"]
            if not math.isfinite(median) or median <= 0:
                raise ValueError(f"Invalid median: {key}")
            cases[key] = median
        required = {
            (layer, workload, backend)
            for layer in LAYERS
            for workload in WORKLOADS
            for backend in BACKENDS
        }
        if set(cases) != required:
            raise ValueError(f"Incomplete or unexpected matrix for Python {python}")
        machine = result["machine_info"]
        cpu = machine.get("cpu", {}).get("brand_raw", machine.get("processor", "unknown"))
        sections.extend(
            [
                f"### CPython {python}",
                "",
                f"Measured: {result['datetime']}. Revision: `{environment['revision']}`"
                + (" (working tree modified)." if environment["dirty"] else "."),
                "",
                f"Environment: {machine['system']} {machine['release']}, {machine['machine']}; {cpu}.",
                "",
                "Dependencies: "
                + ", ".join(
                    f"`{key}=={value}`"
                    for key, value in sorted(environment["dependencies"].items())
                )
                + ".",
                "",
                "| Layer | Workload | json (µs) | orjson (µs; speedup) | msgspec (µs; speedup) |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for layer in LAYERS:
            for workload in WORKLOADS:
                baseline = cases[layer, workload, "json"]
                cells = [f"{baseline * 1e6:.3f}"]
                for backend in BACKENDS[1:]:
                    timing = cases[layer, workload, backend]
                    cells.append(f"{timing * 1e6:.3f}; {baseline / timing:.2f}×")
                sections.append(f"| {layer} | {workload} | " + " | ".join(cells) + " |")
        sections.append("")
    return "\n".join(sections)


def main() -> None:
    """Print a summary or replace the generated section of a documentation page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--update", type=Path, help="Replace the generated section in this page")
    args = parser.parse_args()
    report = render(args.results)
    if args.update:
        text = args.update.read_text()
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        args.update.write_text(before + START + "\n\n" + report + "\n" + END + after)
    else:
        print(report)
    return


if __name__ == "__main__":
    main()
