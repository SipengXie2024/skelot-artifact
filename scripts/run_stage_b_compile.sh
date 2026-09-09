#!/usr/bin/env bash
# Stage B: the dual-arm compile benchmark. This is the RQ2 measurement.
#
#   ./run_stage_b_compile.sh base     # ~11.3 h at 16 threads, 12.4 GB of cache
#   ./run_stage_b_compile.sh arb      # ~2.3 h at 16 threads, 2.0 GB of cache
#
# --mode both produces the Naive per-hash row and the SkelOT row from one run,
# so the two arms see the same machine and the same thread count. The SkelOT row
# carries the EMSE grouping guard counts.
#
# Add --resume by exporting RESUME=1 if a run was interrupted. The .o/.so cache
# carries no compiler fingerprint, so never resume into a cache that was built
# by a different binary: delete the cache directory instead.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN="${1:?usage: run_stage_b_compile.sh <base|arb|eth|bsc>}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
BIN="$(runner_bin skelot_compile_bench)"

SCOPE="full_10k_emse_${CHAIN}"
[[ "${CHAIN}" == "base" ]] && SCOPE="full_10k_emse_sorted"
CACHE="${CACHE_ROOT}/stage_b_emse_${CHAIN}"
OUT="${RESULTS_ROOT}/compile_bench_emse_${CHAIN}.json"
LOG="${RESULTS_ROOT}/logs/stage_b_emse_${CHAIN}_$(skelot_stamp).log"
mkdir -p "${CACHE}"

RESUME_FLAG=()
[[ "${RESUME:-0}" == "1" ]] && RESUME_FLAG=(--resume)

skelot_banner "Stage B (${CHAIN})" >>"${LOG}"
"${BIN}" \
    --bench-dir "${BENCH_DIR}" \
    --start-block "${START}" --block-count "${COUNT}" \
    --mode both --skeleton-mode emse \
    --scope "${SCOPE}" \
    --cache-dir "${CACHE}" \
    --threads "${THREADS}" \
    "${RESUME_FLAG[@]}" \
    --out "${OUT}" 2>&1 | tee -a "${LOG}"

echo "Stage B ${CHAIN} done. JSON: ${OUT}, cache: ${CACHE}, log: ${LOG}"
