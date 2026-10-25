"""Export timing and speedup plots from the committed benchmark summaries."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from benchmark_report import LAYERS, WORKLOADS, comparison_groups, load_results, render

COLORS = {
    "json (CPython)": "#0072B2",
    "orjson (CPython)": "#D55E00",
    "msgspec (CPython)": "#009E73",
    "json (PyPy)": "#CC79A7",
}
MARKERS = {
    "json (CPython)": "o",
    "orjson (CPython)": "s",
    "msgspec (CPython)": "^",
    "json (PyPy)": "D",
}
STYLE = {
    "font.family": "DejaVu Sans",
    "svg.fonttype": "none",
    "svg.hashsalt": "python-json-logger-benchmark",
}


def make_plot(result: dict, kind: str) -> Figure:
    """Compare encoders within each layer, with quartile whiskers for timing plots."""
    backends = result["backends"]
    cases = result["cases"]
    reference = "json (CPython)" if "json (CPython)" in backends else "json (PyPy)"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    for axis, layer in zip(axes, LAYERS):
        for index, backend in enumerate(backends):
            positions = [
                row + (index - (len(backends) - 1) / 2) * 0.22 for row in range(len(WORKLOADS))
            ]
            stats = [cases[layer, workload, backend] for workload in WORKLOADS]
            if kind == "times":
                values = [item["median"] * 1e6 for item in stats]
                errors = [
                    [(item["median"] - item["q1"]) * 1e6 for item in stats],
                    [(item["q3"] - item["median"]) * 1e6 for item in stats],
                ]
                axis.errorbar(
                    values,
                    positions,
                    xerr=errors,
                    fmt=MARKERS[backend],
                    color=COLORS[backend],
                    label=backend,
                    capsize=3,
                    markersize=5,
                )
            else:
                values = [
                    cases[layer, workload, reference]["median"] / item["median"]
                    for workload, item in zip(WORKLOADS, stats)
                ]
                axis.plot(
                    values,
                    positions,
                    linestyle="none",
                    marker=MARKERS[backend],
                    color=COLORS[backend],
                    label=backend,
                    markersize=5,
                )
        axis.set_yticks(range(len(WORKLOADS)), WORKLOADS)
        axis.invert_yaxis()
        axis.set_title("Serialization" if layer == "serialization" else "Complete formatting")
        axis.grid(axis="x", alpha=0.25)
        axis.set_axisbelow(True)
        if kind == "times":
            axis.set_xscale("log")
            axis.set_xlabel("Median time (µs, log scale) — lower is faster")
        else:
            axis.axvline(1, color="#666666", linestyle="--", linewidth=1)
            axis.set_xlim(left=0)
            axis.set_xlabel(f"Speedup vs {reference} — higher is faster")
    title = "Median operation times" if kind == "times" else "Ratios of median times"
    figure.suptitle(f"Python {result['python']}: {title}", fontsize=14)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.065), ncol=len(backends)
    )
    caption = (
        "Whiskers span Q1–Q3 (central 50% of rounds), not confidence intervals."
        if kind == "times"
        else f"Dashed line: {reference} (1×). Descriptive ratios have no confidence intervals."
    )
    figure.text(0.5, 0.025, caption, ha="center", fontsize=9)
    figure.tight_layout(rect=(0, 0.14, 1, 0.92))
    return figure


def main() -> None:
    """Write deterministic SVG files; install the benchmark-report dependency group."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.results)  # Validate matrices and statistics before producing any plots.
    args.output.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context(STYLE):
        for result in comparison_groups(load_results(args.results)):
            for kind in ("times", "speedup"):
                figure = make_plot(result, kind)
                target = args.output / f"python-{result['python']}-{kind}.svg"
                figure.savefig(target, metadata={"Date": None})
                plt.close(figure)
    return


if __name__ == "__main__":
    main()
