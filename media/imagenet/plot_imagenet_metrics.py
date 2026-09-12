#!/usr/bin/env python3
"""Create publication-quality ImageNet training-curve figures from summary CSVs.

The shaded regions use the q10/q90 columns supplied by the CSV files.  If an
interval is unavailable for a metric, the mean curve is still drawn and a
warning is emitted instead of manufacturing an uncertainty estimate.
"""

from __future__ import annotations

import argparse
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl

# Force a non-interactive backend so the script is reliable on headless servers.
mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator, PercentFormatter


@dataclass(frozen=True)
class Experiment:
    key: str
    label: str
    color: str
    linestyle: object = "-"
    linewidth: float = 2.15


# A colorblind-friendly palette.  This single mapping is shared by all plots.
EXPERIMENTS = (
    Experiment("g4", r"group-size $n=4$", "#0072B2"),
    Experiment("g16", r"group-size $n=16$", "#009E73"),
    Experiment("g64", r"group-size $n=64$", "#E69F00"),
    Experiment("g256", r"group-size $n=256$", "#D55E00"),
    Experiment("mle", "maximum likelihood", "#CC79A7", (0, (6, 2.2)), 2.35),
    Experiment(
        "logit-shift", "direct logit-shift", "#4D4D4D", (0, (4, 1.6, 1.2, 1.6)), 2.35
    ),
)


METRICS = (
    ("accuracy", "Accuracy (%)", "imagenet_accuracy.pdf"),
    ("entropy", "Entropy", "imagenet_entropy.pdf"),
    (
        "true_cond_entropy",
        "True conditional entropy",
        "imagenet_true_conditional_entropy.pdf",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing *_summary.csv files (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output" / "pdf",
        help="Destination for the three PDFs (default: output/pdf).",
    )
    return parser.parse_args()


def experiment_key(path: Path) -> str | None:
    """Extract an experiment key without confusing g1 with g16/g256."""
    match = re.search(r"imagenet-rl-(g(?:4|16|64|256)|mle|logit-shift)-", path.name)
    return match.group(1) if match else None


def load_data(input_dir: Path) -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {}
    for path in sorted(input_dir.glob("imagenet-rl-*_summary.csv")):
        key = experiment_key(path)
        if key is None:
            continue
        if key in data:
            raise ValueError(f"Multiple CSV files found for experiment {key!r}")

        frame = pd.read_csv(path).sort_values("step")
        if "step" not in frame or frame["step"].duplicated().any():
            raise ValueError(f"Invalid or duplicated training steps in {path.name}")
        data[key] = frame

    expected = {experiment.key for experiment in EXPERIMENTS}
    missing = expected - data.keys()
    if missing:
        raise FileNotFoundError(f"Missing experiment CSV(s): {', '.join(sorted(missing))}")
    return data


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 10.5,
            "axes.labelsize": 12,
            "axes.labelweight": "medium",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "legend.fontsize": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.transparent": False,
        }
    )


def plot_metric(
    data: dict[str, pd.DataFrame], metric: str, ylabel: str, output_path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.65), constrained_layout=True)
    has_any_band = False

    for experiment in EXPERIMENTS:
        frame = data[experiment.key]
        mean_col = f"{metric}_mean"
        low_col = f"{metric}_q10"
        high_col = f"{metric}_q90"
        if mean_col not in frame:
            raise KeyError(f"Column {mean_col!r} is missing for {experiment.key}")

        x = frame["step"].to_numpy()
        y = frame[mean_col].to_numpy()
        scale = 100.0 if metric == "accuracy" else 1.0

        if low_col in frame and high_col in frame:
            low = frame[low_col].to_numpy() * scale
            high = frame[high_col].to_numpy() * scale
            ax.fill_between(
                x,
                low,
                high,
                color=experiment.color,
                alpha=0.14,
                linewidth=0,
                zorder=1,
            )
            has_any_band = True

        ax.plot(
            x,
            y * scale,
            label=experiment.label,
            color=experiment.color,
            linestyle=experiment.linestyle,
            linewidth=experiment.linewidth,
            solid_capstyle="round",
            zorder=2,
        )

    if not has_any_band:
        warnings.warn(
            f"No q10/q90 columns found for {metric}; plotting mean curves only.",
            stacklevel=2,
        )

    ax.set_xlabel("Training steps")
    ax.set_ylabel(ylabel)
    ax.set_xlim(left=0)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    if metric == "accuracy":
        # Values have already been multiplied by 100; this formatter only adds %.
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.7)
    ax.grid(axis="x", color="#E8E8E8", linewidth=0.55, alpha=0.45)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.margins(x=0, y=0.06)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=3,
        frameon=False,
        handlelength=2.8,
        handletextpad=0.6,
        columnspacing=1.3,
        borderaxespad=0,
    )
    if has_any_band:
        ax.text(
            0.99,
            0.025,
            "shading: q10–q90",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=8.3,
            color="#666666",
        )

    fig.savefig(output_path, format="pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    data = load_data(args.input_dir)

    for metric, ylabel, filename in METRICS:
        output_path = args.output_dir / filename
        plot_metric(data, metric, ylabel, output_path)
        print(f"saved {output_path}")


if __name__ == "__main__":
    main()
