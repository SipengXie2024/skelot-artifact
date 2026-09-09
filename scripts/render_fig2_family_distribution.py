#!/usr/bin/env python3
"""Four-chain family-size distribution, matched log-log rank-size panels.

Each panel ranks that chain's skeletons by how many distinct code hashes share
them, largest first, and plots rank against family size. The head of every
curve is a handful of very large families and the tail is the flat run of
singletons, which is the shape the paper's Section 3 describes.

Input is the Stage A output for each chain, results/<chain>_emse/skeleton_families.json
if you re-ran the scan, otherwise the copy shipped in data/. Output goes to
results/; nothing here writes into the paper repository.

Callout labels come from the protocol_tag field that the scanner records. The
figure in the paper carries richer names (PancakeSwap V3 liquidity-mining
pools, TransparentUpgradeableProxy, ERC1155Creator) which came from a separate
on-chain identification pass, not from this file.
"""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator

from paths import inp, out

# Four unrelated categories, so this keeps its own per-chain palette rather
# than the Naive-versus-SkelOT comparison colours.
PANELS = [
    ("base", "Base", "#0A77B5", "base_emse/skeleton_families.json"),
    ("eth", "Ethereum", "#D6640A", "eth_10k_emse/skeleton_families.json"),
    ("bsc", "BSC", "#0AA278", "bsc_10k_emse/skeleton_families.json"),
    ("arb", "Arbitrum", "#CD7DA9", "arb_10k_emse/skeleton_families.json"),
]

TOP_LABELS = 5
HEAD_MARKERS = 40

# Shared across the four panels so the shapes are directly comparable. Widest
# corpus is Ethereum with 24,406 skeletons; largest family is Base with 3,323.
XLIM = (0.7, 4.0e4)
YLIM = (0.7, 9.0e3)

RC = {"font.size": 7.6, "axes.labelsize": 8.0, "xtick.labelsize": 7.0,
      "ytick.labelsize": 7.0, "pdf.fonttype": 42, "ps.fonttype": 42}


def load(rel):
    fams = json.loads(inp(rel).read_text())["families"]
    sizes = sorted((f["family_size"] for f in fams), reverse=True)
    top = sorted(fams, key=lambda f: -f["family_size"])[:TOP_LABELS]
    return np.array(sizes, dtype=float), top


def short_tag(fam):
    """A callout short enough for a single-column panel."""
    tag = (fam.get("protocol_tag") or "").strip()
    for long, short in (("Uniswap V3 Pool", "UniV3"),
                        ("EIP-1167 minimal proxy (45B)", "EIP-1167"),
                        ("proxy (DELEGATECALL)", "proxy"),
                        ("ERC-20 token", "ERC-20")):
        if tag == long:
            return short
    if tag.startswith(("tiny ", "small ", "medium ", "large ", "huge ")):
        # A size bucket, not an identity: fall back to the skeleton hash.
        return fam["skeleton_hash"][:8]
    return tag or fam["skeleton_hash"][:8]


def main():
    with plt.rc_context(RC):
        fig, axes = plt.subplots(2, 2, figsize=(3.33, 3.1), sharex=True, sharey=True,
                                 gridspec_kw={"hspace": 0.12, "wspace": 0.10})

        for ax, (chain, title, color, rel) in zip(axes.flat, PANELS):
            sizes, top = load(rel)
            rank = np.arange(1, len(sizes) + 1)

            ax.plot(rank, sizes, color=color, lw=1.1, zorder=3)
            head = min(HEAD_MARKERS, len(sizes))
            ax.plot(rank[:head], sizes[:head], "o", color=color, ms=1.9,
                    zorder=4, lw=0)

            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(*XLIM)
            ax.set_ylim(*YLIM)
            ax.xaxis.set_major_locator(LogLocator(base=10, numticks=5))
            ax.yaxis.set_major_locator(LogLocator(base=10, numticks=5))
            ax.grid(True, which="major", ls=":", alpha=0.35, zorder=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            # Annotations must not move the view, and the panels share axes.
            ax.autoscale(False)

            ax.text(0.96, 0.94, title, transform=ax.transAxes, ha="right",
                    va="top", fontsize=8.4, color=color, fontweight="bold")

            # Arrow callouts for the largest families. The labels sit in a
            # fixed stack in panel coordinates and point back at their rank, so
            # they never land on the curve however steep it is.
            for i, fam in enumerate(top):
                ax.annotate(
                    short_tag(fam),
                    xy=(i + 1, fam["family_size"]), xycoords="data",
                    xytext=(0.30 + 0.045 * i, 0.86 - 0.135 * i),
                    textcoords="axes fraction",
                    fontsize=5.4, color="#333333", va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", lw=0.4, color="#888888",
                                    shrinkA=0.5, shrinkB=1.5),
                )

        fig.supxlabel("Family rank", fontsize=8.0, y=0.02)
        fig.supylabel("Family size (#code hashes)", fontsize=8.0, x=0.015)
        fig.subplots_adjust(left=0.135, right=0.99, top=0.99, bottom=0.115)

        dst = out("fig2_family_distribution_xchain.pdf")
        fig.savefig(dst, bbox_inches="tight")
        fig.savefig(dst.with_suffix(".png"), dpi=300, bbox_inches="tight")
        plt.close(fig)

    print(f"wrote {dst}")
    for chain, title, _, rel in PANELS:
        sizes, top = load(rel)
        multi = int((sizes > 1).sum())
        print(f"{title:>9}: {len(sizes):,} skeletons, {multi:,} multi-member, "
              f"largest {int(sizes[0]):,} members")


if __name__ == "__main__":
    main()
