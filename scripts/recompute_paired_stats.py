#!/usr/bin/env python3
"""Recompute RQ3 per-contract statistics with a proper PAIRED test.

The shipped skeleton_vs_perhash.json classified contracts with an UNPAIRED
Welch statistic and a normal (z) p-value approximation. raw_samples retain the
(block, round) pairing, so this script derives, per contract:
  - paired t-test on d_i = per_hash_us_i - skeleton_us_i (Student t, df=n-1)
  - 95% CI on the mean paired difference and on the speedup ratio
  - CI-based verdict: FASTER if the difference CI is entirely > 0,
    SLOWER if entirely < 0, EQUIVALENT if it spans 0
  - Benjamini-Hochberg FDR-corrected verdicts (q=0.05) across all contracts
and aggregates: verdict counts (old vs new vs BH-corrected), speedup
mean/median/geomean, and the distribution of per-contract sample sizes.

Usage: python3 scripts/recompute_paired_stats.py [in.json] [out.json]
Defaults: skeleton_vs_perhash.json -> results/paired_stats_recomputed.json,
with the input resolved under results/ first and data/ second.

The input must carry raw_samples, which the replay driver only writes when
given --emit-raw-samples.
"""

import json
import math
import sys

from scipy import stats

from paths import inp, out


def analyze_contract(rec):
    samples = rec["raw_samples"]
    n = len(samples)
    if n < 2:
        return None
    d = [s["per_hash_us"] - s["skeleton_us"] for s in samples]
    ph = [s["per_hash_us"] for s in samples]
    sk = [s["skeleton_us"] for s in samples]

    mean_d = sum(d) / n
    var_d = sum((x - mean_d) ** 2 for x in d) / (n - 1)
    sd_d = math.sqrt(var_d)

    if sd_d == 0.0:
        t_stat = math.inf if mean_d > 0 else (-math.inf if mean_d < 0 else 0.0)
        p = 0.0 if mean_d != 0 else 1.0
        ci = (mean_d, mean_d)
    else:
        se = sd_d / math.sqrt(n)
        t_stat = mean_d / se
        p = 2.0 * stats.t.sf(abs(t_stat), df=n - 1)
        tcrit = stats.t.ppf(0.975, df=n - 1)
        ci = (mean_d - tcrit * se, mean_d + tcrit * se)

    if ci[0] > 0:
        verdict = "SKELETON_FASTER"
    elif ci[1] < 0:
        verdict = "PER_HASH_FASTER"
    else:
        verdict = "EQUIVALENT"

    speedup = (sum(ph) / n) / (sum(sk) / n) if sum(sk) > 0 else None
    return {
        "code_hash": rec["code_hash"],
        "n": n,
        "mean_diff_us": mean_d,
        "ci95_diff_us": ci,
        "t": None if math.isinf(t_stat) else t_stat,
        "p_paired": p,
        "speedup_ratio": speedup,
        "verdict_paired": verdict,
        "verdict_shipped": rec["verdict"],
        "welch_p_shipped": rec.get("welch_p"),
    }


def geomean(xs):
    xs = [x for x in xs if x and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def apply_bh_verdicts(rows, q=0.05):
    """Benjamini-Hochberg step-up over p_paired; sets verdict_bh on each row."""
    m = len(rows)
    order = sorted(rows, key=lambda r: r["p_paired"])
    k = 0
    for i, r in enumerate(order, 1):
        if r["p_paired"] <= i / m * q:
            k = i
    rejected = set(id(r) for r in order[:k])
    for r in rows:
        if id(r) in rejected:
            r["verdict_bh"] = "SKELETON_FASTER" if r["mean_diff_us"] > 0 else "PER_HASH_FASTER"
        else:
            r["verdict_bh"] = "EQUIVALENT"
    return k


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else inp("skeleton_vs_perhash.json")
    dst = sys.argv[2] if len(sys.argv) > 2 else out("paired_stats_recomputed.json")
    with open(src) as f:
        data = json.load(f)

    rows = [r for r in (analyze_contract(c) for c in data["per_contract"]) if r]
    bh_rejected = apply_bh_verdicts(rows)

    def count(key):
        out = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + 1
        return out

    speedups = sorted(r["speedup_ratio"] for r in rows if r["speedup_ratio"])
    m = len(speedups)
    ns = sorted(r["n"] for r in rows)

    summary = {
        "contracts": len(rows),
        "verdicts_shipped_unpaired_z": count("verdict_shipped"),
        "verdicts_paired_t_ci": count("verdict_paired"),
        "verdicts_bh_fdr_q05": count("verdict_bh"),
        "bh_rejected": bh_rejected,
        "flips": sum(1 for r in rows if r["verdict_paired"] != r["verdict_shipped"]),
        "speedup_mean": sum(speedups) / m,
        "speedup_median": speedups[m // 2] if m % 2 else (speedups[m // 2 - 1] + speedups[m // 2]) / 2,
        "speedup_geomean": geomean(speedups),
        "speedup_p25_p75": (speedups[m // 4], speedups[(3 * m) // 4]),
        "n_min_median_max": (ns[0], ns[len(ns) // 2], ns[-1]),
        "n_eq_5_contracts": sum(1 for x in ns if x == 5),
    }

    with open(dst, "w") as f:
        json.dump({"summary": summary, "per_contract": rows}, f, indent=1)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
