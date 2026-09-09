#!/usr/bin/env python3
"""RQ4 budget under three compile policies, sized for a single acmart column.

Two stacked panels share the coverage axis: artifacts compiled on top, object
footprint below. Palette follows render_all.py: purple is Naive AOT, green is SkelOT. The third
series stays purple because it is the same compiler under a different rule for
choosing what to compile.

Data comes from rq4_three_series.py; run that first if the corpus changes.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from palette import (
    NAIVE_DARK, NAIVE_LIGHT, SKELOT_DARK, SKELOT_LIGHT, NAIVE_DEEP as MATCH_EDGE, AXIS,
)

from paths import inp, out

COLUMN_W = 3.33

RC = {"font.size": 7.6, "axes.labelsize": 7.8, "xtick.labelsize": 7.6,
      "ytick.labelsize": 7.2, "legend.fontsize": 6.2, "pdf.fonttype": 42,
      "ps.fonttype": 42}


def main():
    rows = json.loads(inp("rq4_three_series.json").read_text())["rows"]
    rows = [r for r in rows if r["target"] < 1.0]
    labels = [f"{r['target']:.0%}" for r in rows]
    x = np.arange(len(rows))
    w = 0.26

    series = [
        ("SkelOT", SKELOT_LIGHT, SKELOT_DARK, None,
         [r["skelot_units"] for r in rows], [r["skelot_mb"] for r in rows]),
        ("Naive, own hot set", NAIVE_LIGHT, NAIVE_DARK, None,
         [r["naive_units"] for r in rows], [r["naive_mb"] for r in rows]),
        ("Naive, matching SkelOT", NAIVE_DARK, MATCH_EDGE, None,
         [r["match_units"] for r in rows], [r["match_mb"] for r in rows]),
    ]

    with plt.rc_context(RC):
        fig, axes = plt.subplots(2, 1, figsize=(COLUMN_W, 2.95), sharex=True,
                                 gridspec_kw={"hspace": 0.14})

        for ax, key, ylab in ((axes[0], 4, "Artifacts"),
                              (axes[1], 5, "Footprint (MB)")):
            for k, (name, c, e, hatch, units, mb) in enumerate(series):
                vals = units if key == 4 else mb
                ax.bar(x + (k - 1) * w, vals, w, color=c, edgecolor=e,
                       linewidth=0.55, hatch=hatch, zorder=3,
                       label=name if key == 4 else None)
            ax.set_yscale("log")
            ax.set_ylabel(ylab, labelpad=2)
            ax.tick_params(axis="both", colors=AXIS, length=2.5, pad=1.5)
            ax.grid(True, axis="y", ls=":", alpha=0.35, zorder=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(AXIS)

        # 1-3-10 decade ticks: successive steps differ by ~3x, so gridlines sit
        # at even spacing on a log axis without the clutter of full minor ticks.
        axes[0].set_ylim(5, 12000)
        axes[0].yaxis.set_major_locator(
            FixedLocator([10, 30, 100, 300, 1000, 3000, 10000]))
        axes[0].yaxis.set_minor_locator(NullLocator())
        axes[0].yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{int(v):,}" if v < 1000 else f"{v/1000:g}k"))

        axes[1].set_ylim(1.5, 5000)
        axes[1].yaxis.set_major_locator(
            FixedLocator([3, 10, 30, 100, 300, 1000, 3000]))
        axes[1].yaxis.set_minor_locator(NullLocator())
        axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))

        axes[1].set_xticks(x)
        axes[1].set_xticklabels(labels)
        axes[1].set_xlabel("Execution-time coverage target", labelpad=2)

        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=3, frameon=False,
                   bbox_to_anchor=(0.54, 1.005), columnspacing=1.15,
                   handlelength=1.05, handletextpad=0.42, borderaxespad=0.0)

        fig.subplots_adjust(left=0.155, right=0.995, top=0.955, bottom=0.135)
        dst = out("fig8_coverage_budget.pdf")
        fig.savefig(dst, bbox_inches="tight")
        fig.savefig(dst.with_suffix(".png"), dpi=300, bbox_inches="tight")
        plt.close(fig)

    print(f"wrote {dst} ({COLUMN_W}in wide, single column)")


if __name__ == "__main__":
    main()
