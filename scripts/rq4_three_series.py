#!/usr/bin/env python3
"""RQ4 budget under three compile policies, artifacts and footprint.

per-hash / own hot set      : compile individual contracts, hottest first
SkelOT   / own hot set      : compile family units, hottest first
per-hash / matching SkelOT  : compile every member of SkelOT's chosen units

Writes data/rq4_three_series.json. Exclusive per-contract timing, EMSE
818-family grouping, object sizes from the sorted EMSE build.
"""

import collections
import json

import numpy as np

from paths import inp, open_text, out

TARGETS = (0.50, 0.75, 0.90, 0.95, 0.99)


def load():
    t = collections.Counter()
    with open_text(inp("exclusive_per_block_base10k.tsv",
                       "exclusive_per_block_base10k.tsv.zst")) as f:
        for line in f:
            _, _, h, us = line.rstrip("\n").split("\t")
            t[h] += float(us)

    fam = {}
    with open(inp("family_map_emse_base.tsv")) as f:
        for line in f:
            h, u = line.rstrip("\n").split("\t")
            fam[h] = u

    recs = json.loads(inp("compile_bench_emse_base_sorted.json").read_text())
    recs = recs["records"] if isinstance(recs, dict) else recs
    pick = lambda m: next(r for r in recs
                          if r.get("scope") == "full_10k_emse_sorted" and r["mode"] == m)
    ph, sk = pick("per_hash"), pick("skelot")
    hash_bytes = dict(zip(ph["compile_unit_hashes"], ph["per_unit_o_bytes"]))
    unit_bytes = dict(zip(sk["compile_unit_hashes"], sk["per_unit_o_bytes"]))
    fam_bytes = {f"fam_{f['skeleton_hash'][:16]}": f["o_bytes"] for f in sk["per_family"]}
    return t, fam, hash_bytes, unit_bytes, fam_bytes, ph, sk


def main():
    t, fam, hash_bytes, unit_bytes, fam_bytes, ph, sk = load()
    total = sum(t.values())
    unit_of = lambda h: fam.get(h, f"solo_{h}")

    # SkelOT unit -> (time, members, object bytes)
    utime, umembers = collections.Counter(), collections.defaultdict(list)
    for h, v in t.items():
        u = unit_of(h)
        utime[u] += v
        umembers[u].append(h)

    def unit_size(u):
        if u in fam_bytes:
            return fam_bytes[u]
        h = u[len("solo_"):] if u.startswith("solo_") else u
        return unit_bytes.get(h, hash_bytes.get(h, 0))

    naive = sorted(t.items(), key=lambda kv: -kv[1])
    n_cum = np.cumsum([v for _, v in naive]) / total
    n_bytes = np.cumsum([hash_bytes.get(h, 0) for h, _ in naive])

    ranked = sorted(utime.items(), key=lambda kv: -kv[1])
    s_cum = np.cumsum([v for _, v in ranked]) / total
    s_bytes = np.cumsum([unit_size(u) for u, _ in ranked])
    m_count = np.cumsum([len(umembers[u]) for u, _ in ranked])
    m_bytes = np.cumsum([sum(hash_bytes.get(h, 0) for h in umembers[u])
                         for u, _ in ranked])

    rows = []
    for tgt in TARGETS:
        ns = int(np.searchsorted(n_cum, tgt) + 1)
        ss = int(np.searchsorted(s_cum, tgt) + 1)
        rows.append(dict(
            target=tgt,
            skelot_units=ss, skelot_mb=s_bytes[ss - 1] / 1e6,
            naive_units=ns, naive_mb=n_bytes[ns - 1] / 1e6,
            match_units=int(m_count[ss - 1]), match_mb=m_bytes[ss - 1] / 1e6))

    rows.append(dict(target=1.0, skelot_units=sk["n_units"],
                     skelot_mb=sk["total_o_bytes"] / 1e6,
                     naive_units=ph["n_units"], naive_mb=ph["total_o_bytes"] / 1e6,
                     match_units=ph["n_units"], match_mb=ph["total_o_bytes"] / 1e6))

    out("rq4_three_series.json").write_text(json.dumps(
        {"total_exec_us": total, "rows": rows}, indent=2))

    hdr = (f"{'target':>7} | {'SkelOT':>7} {'MB':>7} | {'per-hash own':>13} {'MB':>7}"
           f" | {'per-hash match':>15} {'MB':>8} | {'sel-':>5} {'share':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        sel = 1 - r["skelot_units"] / r["naive_units"]
        share = r["match_units"] / r["skelot_units"]
        print(f"{r['target']:>6.0%} | {r['skelot_units']:>7,} {r['skelot_mb']:>7.1f} "
              f"| {r['naive_units']:>13,} {r['naive_mb']:>7.1f} "
              f"| {r['match_units']:>15,} {r['match_mb']:>8.1f} "
              f"| {sel:>5.0%} {share:>6.1f}x")


if __name__ == "__main__":
    main()
