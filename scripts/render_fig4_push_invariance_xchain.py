#!/usr/bin/env python3
"""Render cross-chain PUSH-byte invariant share figure from Table 3 values."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from palette import AXIS as AXIS_COLOR

from paths import out

CHAINS = ["Base", "Ethereum", "BSC", "Arbitrum"]
MULTI_FAMS = [825, 1833, 632, 173]
INV_SHARE = [94.92, 95.89, 96.91, 93.72]

# Four unrelated categories (chains), not a Naive-vs-SkelOT comparison, so this
# keeps its own four-colour palette rather than importing from palette.py.
COLORS = ["#0A77B5", "#D6640A", "#0AA278", "#CD7DA9"]
BAR_HATCH = "/"

RC = {
    "font.size": 11,
    "axes.labelsize": 12,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 10,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def render(out_path: Path) -> None:
    y = np.arange(len(CHAINS))

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(4.15, 2.55))
        ax.barh(
            y,
            INV_SHARE,
            height=0.56,
            color=COLORS,
            alpha=0.88,
            edgecolor="white",
            linewidth=0.7,
            hatch=BAR_HATCH,
            zorder=3,
        )

        for yi, share, fams in zip(y, INV_SHARE, MULTI_FAMS):
            ax.text(
                share + 0.16,
                yi,
                f"{share:.2f}%  (n={fams})",
                va="center",
                ha="left",
                fontsize=9.4,
                color="#111111",
            )

        ax.set_yticks(y)
        ax.set_yticklabels(CHAINS)
        ax.invert_yaxis()
        ax.set_xlim(90, 98)
        ax.set_xticks([90, 92, 94, 96, 98])
        ax.set_xlabel("Invariant PUSH-byte share (%)")
        ax.xaxis.label.set_size(10.0)
        ax.grid(True, axis="x", linestyle=":", alpha=0.35, zorder=0)
        ax.tick_params(axis="both", colors=AXIS_COLOR)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(AXIS_COLOR)
        ax.spines["bottom"].set_color(AXIS_COLOR)
        fig.text(
            0.50,
            0.055,
            "n = multi-member families on that chain",
            ha="center",
            va="center",
            fontsize=7.2,
            color="#555555",
        )

        fig.tight_layout(pad=0.35)
        fig.subplots_adjust(bottom=0.24)
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)

    print(f"wrote {out_path}")


def main() -> None:
    render(out("fig4_push_invariance_xchain.pdf"))


if __name__ == "__main__":
    main()
