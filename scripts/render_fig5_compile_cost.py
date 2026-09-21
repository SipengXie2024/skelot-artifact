#!/usr/bin/env python3
"""Render the compile-side cost figure (Figure 5) from the Base compile
benchmark JSON: results/compile_bench_emse_base_sorted.json when a fresh run
produced it, otherwise the shipped reference copy in data/ (see paths.inp)."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from palette import NAIVE_LIGHT as NAIVE_COLOR, SKELOT_LIGHT as SKELOT_COLOR, \
    NAIVE_DARK as NAIVE_EDGE, SKELOT_DARK as SKELOT_EDGE, AXIS as AXIS_COLOR

from paths import inp, out

def load_metrics():
    """The three RQ2 headline pairs, Naive per-hash against SkelOT, from the
    full_10k_emse_sorted records: unit count, summed compile seconds, and
    summed object bytes."""
    doc = json.loads(inp("compile_bench_emse_base_sorted.json").read_text())
    recs = doc["records"] if isinstance(doc, dict) else doc
    by_mode = {r["mode"]: r for r in recs if r.get("scope") == "full_10k_emse_sorted"}
    ph, sk = by_mode["per_hash"], by_mode["skelot"]
    units = (ph["n_units"], sk["n_units"])
    secs = (ph["total_compile_seconds"], sk["total_compile_seconds"])
    gb = (ph["total_o_bytes"] / 1e9, sk["total_o_bytes"] / 1e9)
    return [
        ("Units", units[0], units[1], f"{units[0]:,}", f"{units[1]:,}", None),
        ("Compile time", secs[0], secs[1], f"{secs[0]:,.0f} s", f"{secs[1]:,.0f} s",
         f"{secs[0] / secs[1]:.2f}×"),
        ("Object footprint", gb[0], gb[1], f"{gb[0]:.2f} GB", f"{gb[1]:.2f} GB",
         f"{100 * (gb[1] / gb[0] - 1):.1f}%"),
    ]

RC = {
    "font.size": 9.5,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 9.2,
    "ytick.labelsize": 9.2,
    "legend.fontsize": 9.2,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def render(out_path: Path) -> None:
    metrics = load_metrics()
    width = 0.34
    xpos = [0.0, 0.42]

    with plt.rc_context(RC):
        fig, axes = plt.subplots(1, 3, figsize=(5.4, 2.55), sharey=True)

        for idx, (ax, (label, naive_raw, skelot_raw, naive_text, skelot_text, effect_text)) in enumerate(zip(axes, metrics)):
            values = [1.0, skelot_raw / naive_raw]
            bars = []
            for x, value, color, edge in zip(
                xpos,
                values,
                [NAIVE_COLOR, SKELOT_COLOR],
                [NAIVE_EDGE, SKELOT_EDGE],
            ):
                bars.append(
                    ax.bar(
                        x,
                        value,
                        width,
                        color=color,
                        edgecolor=edge,
                        linewidth=0.8,
                        zorder=3,
                    )[0]
                )

            ax.text(
                bars[0].get_x() + bars[0].get_width() / 2,
                bars[0].get_height() + 0.045,
                naive_text,
                ha="center",
                va="bottom",
                fontsize=8.2,
                color="#111111",
            )
            ax.text(
                bars[1].get_x() + bars[1].get_width() / 2,
                bars[1].get_height() + 0.045,
                skelot_text,
                ha="center",
                va="bottom",
                fontsize=8.2,
                color="#111111",
            )

            ax.set_title(label, pad=9)
            ax.set_xticks(xpos)
            ax.set_xticklabels(["Naive", "SkelOT"])
            ax.set_ylim(0, 1.38)
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0, 1.25])
            ax.tick_params(axis="both", colors=AXIS_COLOR)
            ax.grid(True, axis="y", linestyle=":", alpha=0.35, zorder=0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(AXIS_COLOR)
            ax.spines["bottom"].set_color(AXIS_COLOR)
            if idx != 0:
                ax.spines["left"].set_visible(False)
                ax.tick_params(axis="y", left=False, labelleft=False)

        axes[0].set_ylabel("Cost normalized to Naive AOT")

        handles = [
            plt.Rectangle((0, 0), 1, 1, facecolor=NAIVE_COLOR, edgecolor=NAIVE_EDGE, linewidth=0.8),
            plt.Rectangle((0, 0), 1, 1, facecolor=SKELOT_COLOR, edgecolor=SKELOT_EDGE, linewidth=0.8),
        ]
        fig.legend(handles, ["Naive AOT", "SkelOT"], loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.03), columnspacing=1.1, handletextpad=0.5)

        fig.tight_layout(pad=0.35, w_pad=0.9)
        fig.subplots_adjust(top=0.78)
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)

    print(f"wrote {out_path}")


def main() -> None:
    render(out("fig5_compile_cost.pdf"))


if __name__ == "__main__":
    main()
