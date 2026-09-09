#!/usr/bin/env python3
"""
EMSE cross-chain consistency: any code_hash appearing in multiple chains'
EMSE skeleton_mapping.tsv files must map to the same EMSE skeleton hash.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

from paths import inp

CHAINS = ("base", "eth", "bsc", "arb")
CHAIN_DIR = {
    "base": "base_emse",
    "eth": "eth_10k_emse",
    "bsc": "bsc_10k_emse",
    "arb": "arb_10k_emse",
}


def load_mapping(chain: str) -> dict[str, str]:
    p = inp(f"{CHAIN_DIR[chain]}/skeleton_mapping.tsv")
    out = {}
    with p.open() as f:
        for row in csv.reader(f, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            skel_hash, code_hash = row[0], row[1]
            out[code_hash] = skel_hash
    return out


def main() -> None:
    maps = {c: load_mapping(c) for c in CHAINS}
    overlap = defaultdict(dict)
    for chain, mapping in maps.items():
        for code_hash, skel_hash in mapping.items():
            overlap[code_hash][chain] = skel_hash

    multi = {h: cs for h, cs in overlap.items() if len(cs) >= 2}
    print(
        "unique code_hashes per chain: "
        + ", ".join(f"{c}={len(maps[c]):,}" for c in CHAINS)
    )
    print(f"code_hashes seen on >=2 chains: {len(multi):,}")

    keyset_counts = defaultdict(int)
    for chains in multi.values():
        keyset_counts[tuple(sorted(chains.keys()))] += 1
    for keyset, count in sorted(keyset_counts.items()):
        print(f"  {'+'.join(keyset)}: {count:,} code_hashes")
    all_four_key = tuple(sorted(CHAINS))
    print(f"code_hashes seen on all 4 chains: {keyset_counts[all_four_key]:,}")

    mismatches = []
    for code_hash, chains in multi.items():
        if len(set(chains.values())) > 1:
            mismatches.append((code_hash, chains))
    if mismatches:
        print(
            f"MISMATCH: {len(mismatches)} code_hashes have differing EMSE skeletons across chains"
        )
        for code_hash, chains in mismatches[:10]:
            print(
                f"  {code_hash}: "
                + ", ".join(f"{c}={s[:10]}" for c, s in chains.items())
            )
        sys.exit(1)

    print(f"OK: all {len(multi):,} cross-chain code_hashes have identical EMSE skeletons")

    skeleton_chains = defaultdict(set)
    for chain, mapping in maps.items():
        for skel_hash in mapping.values():
            skeleton_chains[skel_hash].add(chain)
    multi_skeletons = {s: cs for s, cs in skeleton_chains.items() if len(cs) >= 2}
    all_four_skeletons = sum(1 for cs in skeleton_chains.values() if tuple(sorted(cs)) == all_four_key)
    print(f"EMSE skeleton hashes seen on >=2 chains: {len(multi_skeletons):,}")
    print(f"EMSE skeleton hashes seen on all 4 chains: {all_four_skeletons:,}")


if __name__ == "__main__":
    main()
