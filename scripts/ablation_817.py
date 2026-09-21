#!/usr/bin/env python3
"""Three-mode compile-side ablation over all 817 shared families.

Naive       sum of each member's own per-hash compile cost
SkelOT      one shared artifact per family, invariants baked in
All-variant one shared artifact per family, every constant in the table

Times are per-unit wall clock summed over the units in a bucket, i.e. what a
serial build would take. The 16-thread wall clock for the whole corpus lives in
the compile_bench records. Sizes are plain sums and carry no such caveat.

Buckets follow bucket_for_raw_len; tiny (5 families) is folded into small.
Writes data/ablation_817.json.
"""

import collections
import json

from paths import RESOLVED, inp, out

ORDER = ["small", "medium", "large", "huge"]


def record(path, scope, mode):
    doc = json.loads(inp(path).read_text())
    recs = doc["records"] if isinstance(doc, dict) else doc
    return next(r for r in recs if r.get("scope") == scope and r["mode"] == mode)


def main():
    sp = record("compile_bench_emse_base_sorted.json", "full_10k_emse_sorted", "skelot")
    ph = record("compile_bench_emse_base_sorted.json", "full_10k_emse_sorted", "per_hash")
    av = record("compile_bench_emse_base_allvariant.json", "full_10k_emse_allvariant", "skelot")

    hash_ms = dict(zip(ph["compile_unit_hashes"], ph["per_unit_ms"]))
    hash_by = dict(zip(ph["compile_unit_hashes"], ph["per_unit_o_bytes"]))

    members = collections.defaultdict(list)
    with open(inp("family_map_emse_base.tsv")) as f:
        for line in f:
            h, u = line.rstrip("\n").split("\t")
            if u.startswith("fam_"):
                members[u[4:]].append(h)

    bucket = {f["skeleton_hash"]: f["bucket"] for f in
              json.loads(inp("base_emse/skeleton_families.json").read_text())["families"]}

    split = {f["skeleton_hash"]: f for f in sp["per_family"]}
    allvar = {f["skeleton_hash"]: f for f in av["per_family"]}

    agg = collections.defaultdict(collections.Counter)
    for key, s in split.items():
        b = bucket[key]
        b = "small" if b == "tiny" else b
        a = agg[b]
        a["families"] += 1
        a["members"] += len(members[key])
        a["naive_s"] += sum(hash_ms[h] for h in members[key]) / 1000.0
        a["naive_b"] += sum(hash_by[h] for h in members[key])
        a["skelot_s"] += s["compile_seconds"]
        a["skelot_b"] += s["o_bytes"]
        a["allvar_s"] += allvar[key]["compile_seconds"]
        a["allvar_b"] += allvar[key]["o_bytes"]

    rows, total = [], collections.Counter()
    for b in ORDER:
        v = agg[b]
        total.update(v)
        rows.append(dict(bucket=b, families=int(v["families"]), members=int(v["members"]),
                         naive_s=v["naive_s"], skelot_s=v["skelot_s"], allvar_s=v["allvar_s"],
                         naive_mb=v["naive_b"] / 1e6, skelot_mb=v["skelot_b"] / 1e6,
                         allvar_mb=v["allvar_b"] / 1e6))

    result = dict(rows=rows,
               total=dict(families=int(total["families"]), members=int(total["members"]),
                          naive_s=total["naive_s"], skelot_s=total["skelot_s"],
                          allvar_s=total["allvar_s"], naive_mb=total["naive_b"] / 1e6,
                          skelot_mb=total["skelot_b"] / 1e6, allvar_mb=total["allvar_b"] / 1e6),
               corpus_wall=dict(naive_s=ph["total_compile_seconds"],
                                skelot_s=sp["total_compile_seconds"]))
    result["inputs"] = [str(p) for p in RESOLVED]
    out("ablation_817.json").write_text(json.dumps(result, indent=2))

    hdr = (f"{'bucket':>7} {'fams':>5} {'memb':>6} | {'Naive':>8} {'SkelOT':>7} {'AV':>7} "
           f"| {'Naive':>8} {'SkelOT':>7} {'AV':>6}")
    print(hdr + "\n" + "-" * len(hdr))
    for r in rows:
        print(f"{r['bucket']:>7} {r['families']:>5} {r['members']:>6,} | "
              f"{r['naive_s']:>8,.0f} {r['skelot_s']:>7,.0f} {r['allvar_s']:>7,.0f} | "
              f"{r['naive_mb']:>8,.1f} {r['skelot_mb']:>7,.1f} {r['allvar_mb']:>6,.1f}")
    t = result["total"]
    print(f"{'all':>7} {t['families']:>5} {t['members']:>6,} | "
          f"{t['naive_s']:>8,.0f} {t['skelot_s']:>7,.0f} {t['allvar_s']:>7,.0f} | "
          f"{t['naive_mb']:>8,.1f} {t['skelot_mb']:>7,.1f} {t['allvar_mb']:>6,.1f}")
    print(f"\nvs SkelOT: Naive {t['naive_s']/t['skelot_s']:.1f}x time, "
          f"{t['naive_mb']/t['skelot_mb']:.1f}x size; "
          f"all-variant {t['allvar_s']/t['skelot_s']:.2f}x, {t['allvar_mb']/t['skelot_mb']:.2f}x")


if __name__ == "__main__":
    main()
