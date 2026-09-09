#!/usr/bin/env python3
"""Per-pair runtime speedup distribution, the RQ3 figure.

One histogram of the per-member speedup ratio on a log x axis, with the median
marked and the quartiles and p95 annotated. Extracted from the paper's
historical render_all.py, which needed pandas and a data file that no longer
exists; this version reads only paired_stats_recomputed.json, the same file the
RQ3 prose and the figure caption are quoted from.

Run recompute_paired_stats.py first if you re-measured the paired replay.
"""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from palette import NAIVE_DARK, SKELOT_DARK, AXIS, NO_CHANGE
from paths import inp, out

RC = {"font.size": 11, "axes.labelsize": 12, "axes.titlesize": 12,
      "xtick.labelsize": 10.5, "ytick.labelsize": 10.5, "legend.fontsize": 10,
      "pdf.fonttype": 42, "ps.fonttype": 42}


def main():
    doc = json.loads(inp("paired_stats_recomputed.json").read_text())
    speedups = [c["speedup_ratio"] for c in doc["per_contract"]
                if c.get("speedup_ratio") is not None]
    if not speedups:
        raise SystemExit("no speedup_ratio values in the input")

    p25, p50, p75, p95 = (float(np.percentile(speedups, q)) for q in (25, 50, 75, 95))

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(4.15, 2.9))

        bins = np.logspace(np.log10(0.4), np.log10(5.5), 40)
        counts, _, _ = ax.hist(speedups, bins=bins, color=SKELOT_DARK, alpha=0.86,
                               edgecolor="white", linewidth=0.55, zorder=3)
        ax.set_xscale("log")
        ymax = float(counts.max()) * 1.30
        ax.set_ylim(0, ymax)

        ax.axvline(1.0, color=NO_CHANGE, ls="--", lw=1.25, zorder=4)
        for v in (p25, p75, p95):
            ax.axvline(v, color="#5f6368", ls=":", lw=1.0, zorder=4)
        ax.axvline(p50, color=NAIVE_DARK, ls="-", lw=1.4, zorder=5)

        for v, label, color in ((p25, f"p25 {p25:.2f}x", "#4a4a4a"),
                                (p50, f"p50 {p50:.2f}x", NAIVE_DARK),
                                (p75, f"p75 {p75:.2f}x", "#4a4a4a"),
                                (p95, f"p95 {p95:.2f}x", "#4a4a4a")):
            ax.text(v, ymax * 0.97, label, fontsize=8.8, ha="left", va="top",
                    rotation=90, color=color)

        ax.xaxis.set_major_locator(FixedLocator([0.5, 1.0, 1.5, 2.0, 3.0, 5.0]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}×"))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlim(0.4, 5.5)

        ax.set_xlabel(f"Per-pair speedup ratio (n = {len(speedups):,})")
        ax.set_ylabel("Family-member pairs")
        ax.tick_params(axis="both", colors=AXIS)
        ax.grid(True, axis="y", ls=":", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(AXIS)
        ax.spines["bottom"].set_color(AXIS)

        fig.tight_layout()
        dst = out("fig7_runtime_speedup_distribution.pdf")
        fig.savefig(dst, bbox_inches="tight", dpi=150)
        fig.savefig(dst.with_suffix(".png"), dpi=300, bbox_inches="tight")
        plt.close(fig)

    print(f"wrote {dst}")
    print(f"n={len(speedups):,}  p25={p25:.3f}  p50={p50:.3f}  "
          f"p75={p75:.3f}  p95={p95:.3f}")


if __name__ == "__main__":
    main()
