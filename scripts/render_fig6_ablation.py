#!/usr/bin/env python3
"""Compile-side ablation over all 817 shared families, one acmart column.

Two stacked panels share the bucket axis, matching fig7: compile time on top,
object size below. Colour identifies the mode, following the fig7 palette.
Run ablation_817.py first to regenerate the data.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from palette import (
    NAIVE_LIGHT, NAIVE_DARK, SKELOT_LIGHT, SKELOT_DARK, ALLVAR_LIGHT, ALLVAR_DARK, AXIS,
)

from paths import inp, out

RC = {"font.size": 7.6, "axes.labelsize": 7.8, "xtick.labelsize": 7.6,
      "ytick.labelsize": 7.2, "legend.fontsize": 6.2, "pdf.fonttype": 42,
      "ps.fonttype": 42}


def main():
    doc = json.loads(inp("ablation_817.json").read_text())
    rows = doc["rows"]
    x = np.arange(len(rows))
    w = 0.26

    modes = [
        ("Naive AOT", NAIVE_LIGHT, NAIVE_DARK, "naive_s", "naive_mb"),
        ("SkelOT", SKELOT_LIGHT, SKELOT_DARK, "skelot_s", "skelot_mb"),
        ("All-variant", ALLVAR_LIGHT, ALLVAR_DARK, "allvar_s", "allvar_mb"),
    ]

    with plt.rc_context(RC):
        fig, axes = plt.subplots(2, 1, figsize=(3.33, 2.95), sharex=True,
                                 gridspec_kw={"hspace": 0.14})

        for ax, key, ylab in ((axes[0], 3, "Compile time (s)"),
                              (axes[1], 4, "Object size (MB)")):
            for k, (name, fill, edge, f_time, f_size) in enumerate(modes):
                field = f_time if key == 3 else f_size
                ax.bar(x + (k - 1) * w, [r[field] for r in rows], w, color=fill,
                       edgecolor=edge, linewidth=0.55, zorder=3,
                       label=name if key == 3 else None)
            ax.set_yscale("log")
            ax.set_ylabel(ylab, labelpad=2)
            ax.tick_params(axis="both", colors=AXIS, length=2.5, pad=1.5)
            ax.grid(True, axis="y", ls=":", alpha=0.35, zorder=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(AXIS)

        axes[0].set_ylim(8, 900_000)
        axes[0].yaxis.set_major_locator(
            FixedLocator([10, 100, 1000, 10000, 100000]))
        axes[0].yaxis.set_minor_locator(NullLocator())
        axes[0].yaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{int(v)}" if v < 1000 else f"{v/1000:g}k"))

        axes[1].set_ylim(0.4, 12000)
        axes[1].yaxis.set_major_locator(FixedLocator([1, 10, 100, 1000]))
        axes[1].yaxis.set_minor_locator(NullLocator())
        axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))

        axes[1].set_xticks(x)
        axes[1].set_xticklabels([f"{r['bucket']}\n{r['families']} fam."
                                 for r in rows])

        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=3, frameon=False,
                   bbox_to_anchor=(0.54, 1.005), columnspacing=1.15,
                   handlelength=1.05, handletextpad=0.42, borderaxespad=0.0)
        fig.subplots_adjust(left=0.165, right=0.995, top=0.955, bottom=0.145)
        dst = out("fig6_ablation.pdf")
        fig.savefig(dst, bbox_inches="tight")
        fig.savefig(dst.with_suffix(".png"), dpi=300, bbox_inches="tight")
        plt.close(fig)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
