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
STYLE = {
    "font.family": "DejaVu Sans",
    "svg.fonttype": "none",
    "svg.hashsalt": "python-json-logger-benchmark",
}


def make_speedup_plot(result: dict) -> Figure:
    """Compare grouped speedup bars in two panels with workload boundaries."""
    backends = result["backends"]
    cases = result["cases"]
    reference = "json (CPython)" if "json (CPython)" in backends else "json (PyPy)"
    figure, axes = plt.subplots(1, 2, figsize=(13, 8))
    height = 0.8 / len(backends)
    for axis, layer in zip(axes, LAYERS):
        upper = 1.0
        for index, backend in enumerate(backends):
            positions = [row - 0.4 + height * (index + 0.5) for row in range(len(WORKLOADS))]
            values = [
                cases[layer, workload, reference]["median"]
                / cases[layer, workload, backend]["median"]
                for workload in WORKLOADS
            ]
            upper = max(upper, max(values))
            axis.barh(
                positions,
                values,
                height=height * 0.85,
                color=COLORS[backend],
                label=backend,
                zorder=2,
            )
            for position, value in zip(positions, values):
                axis.annotate(
                    f"{value:.2g}×",
                    (value, position),
                    xytext=(4, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=8,
                )
        axis.set_yticks(range(len(WORKLOADS)), WORKLOADS)
        axis.set_ylim(len(WORKLOADS) - 0.5, -0.5)
        axis.set_xlim(0, upper * 1.2)
        for row in range(len(WORKLOADS)):
            if row % 2 == 0:
                axis.axhspan(row - 0.5, row + 0.5, color="#000000", alpha=0.045, zorder=0)
            axis.axhline(row + 0.5, color="#888888", alpha=0.3, linewidth=0.7)
        axis.axvline(1, color="#444444", linestyle="--", linewidth=1, zorder=3)
        axis.set_title("Serialization" if layer == "serialization" else "Complete formatting")
        axis.set_xlabel("Speedup (×) — higher is faster")
        axis.grid(axis="x", alpha=0.25)
        axis.set_axisbelow(True)
    figure.suptitle(f"Python {result['python']}: Ratios of median times", fontsize=15)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.065), ncol=len(backends)
    )
    figure.text(
        0.5,
        0.025,
        f"Dashed line: {reference} (1×). Descriptive ratios have no confidence intervals.",
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.14, 1, 0.94))
    return figure


def make_plot(result: dict, kind: str) -> Figure:
    """Compare labeled horizontal bars in separate linear-scale workload panels."""
    if kind == "speedup":
        return make_speedup_plot(result)
    backends = result["backends"]
    cases = result["cases"]
    figure, axes = plt.subplots(len(WORKLOADS), len(LAYERS), figsize=(13, 16))
    for row, workload in enumerate(WORKLOADS):
        for col, layer in enumerate(LAYERS):
            axis = axes[row, col]
            stats = [cases[layer, workload, backend] for backend in backends]
            values = [item["median"] * 1e6 for item in stats]
            ends = [item["q3"] * 1e6 for item in stats]
            labels = [f"{value:.3g}" for value in values]
            axis.barh(
                range(len(backends)),
                values,
                height=0.65,
                color=[COLORS[backend] for backend in backends],
                alpha=0.85,
                zorder=2,
            )
            axis.errorbar(
                values,
                range(len(backends)),
                xerr=[
                    [(item["median"] - item["q1"]) * 1e6 for item in stats],
                    [(item["q3"] - item["median"]) * 1e6 for item in stats],
                ],
                fmt="none",
                ecolor="#222222",
                capsize=3,
                linewidth=1,
                zorder=3,
            )
            upper = max(ends)
            for index, label in enumerate(labels):
                axis.text(ends[index] + upper * 0.025, index, label, va="center", fontsize=9)
            axis.set_yticks(range(len(backends)), backends, fontsize=9)
            axis.invert_yaxis()
            axis.set_xlim(0, upper * 1.23)
            layer_title = "Serialization" if layer == "serialization" else "Complete formatting"
            axis.set_title(f"{workload} · {layer_title}", fontsize=11)
            axis.set_xlabel("Median time (µs)", fontsize=9)
            axis.grid(axis="x", alpha=0.25, zorder=0)
            axis.set_axisbelow(True)
            axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle(f"Python {result['python']}: Median operation times", fontsize=15)
    caption = (
        "Every panel starts at zero; axis ranges differ by panel. Lower is faster.\n"
        "Whiskers span Q1–Q3, not confidence intervals. Labels show median µs."
    )
    figure.text(0.5, 0.012, caption, ha="center", fontsize=10)
    figure.tight_layout(rect=(0, 0.045, 1, 0.97), h_pad=1.5, w_pad=2)
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
                target.write_text(
                    "\n".join(
                        line.rstrip() for line in target.read_text(encoding="utf-8").splitlines()
                    )
                    + "\n",
                    encoding="utf-8",
                )
                plt.close(figure)
    return


if __name__ == "__main__":
    main()
