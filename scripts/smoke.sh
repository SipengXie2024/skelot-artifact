#!/usr/bin/env bash
# Minimal working example. Builds the prototype and exercises the whole path
# (skeleton extraction, family grouping, admission guards, per-member table
# lowering, dual-mode dispatch) on a 20-block slice of the Base corpus.
#
#   ./smoke.sh
#
# Needs only the smoke slice of the corpus, about 100 MB:
#   ../data/fetch_data.sh --smoke base
#
# Roughly 2 minutes to build, seconds for the grouping step, and a few minutes
# for the single-block execution check, which compiles that block's contracts
# under both designs before replaying it.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN=base
START=38004930
BENCH_DIR="$(corpus_dir "${CHAIN}")"
LOG="${RESULTS_ROOT}/logs/smoke_$(skelot_stamp).log"

echo "[1/3] building the runner (release)"
(cd "${REVMC_ROOT}" && cargo build --release -p revmc-examples-runner) 2>&1 | tee -a "${LOG}"

echo
echo "[2/3] family grouping and admission guards over 20 blocks"
echo "      expect 91 multi-member families covering 578 members, 1,140 per-hash units,"
echo "      1,231 compile units, no g1/g2 rejections on this slice, 0 hash-collision splits"
"$(runner_bin grouping_stats)" \
    --bench-dir "${BENCH_DIR}" \
    --start-block "${START}" --block-count 20 \
    --skeleton-mode emse --time-analysis 2>&1 | tee -a "${LOG}"

echo
echo "[3/3] single-block execution check, both designs against the interpreter"
echo "      expect 18 skeleton groups over 67 contracts and 228/228 transactions matching"
echo "      with gas 30886502 EQUAL"
"$(runner_bin skeleton_bench)" \
    --bench-dir "${BENCH_DIR}" \
    --block "${START}" --rounds 5 --warmup 2 \
    --skeleton-mode emse \
    --out "${RESULTS_ROOT}/smoke_exec_sanity.json" 2>&1 | tee -a "${LOG}"

echo
echo "smoke run finished. Log: ${LOG}"
