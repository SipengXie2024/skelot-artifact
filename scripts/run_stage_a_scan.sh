#!/usr/bin/env bash
# Stage A: static corpus scan for one chain.
#
#   ./run_stage_a_scan.sh base
#
# Produces dataset_scan.json, skeleton_families.json and skeleton_mapping.tsv
# under $RESULTS_ROOT/<chain>_emse. Feeds Table 1, Table 2, Section 6.1, and
# Figure 2. Single-threaded. Base took 922.9 s, Ethereum 886.4 s, BSC 84.5 s,
# Arbitrum 125.1 s.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN="${1:?usage: run_stage_a_scan.sh <base|eth|bsc|arb>}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
BIN="$(runner_bin skelot_dataset_scan)"

OUT_DIR="${RESULTS_ROOT}/${CHAIN}_emse"
LOG="${RESULTS_ROOT}/logs/stage_a_${CHAIN}_$(skelot_stamp).log"
mkdir -p "${OUT_DIR}"

skelot_banner "Stage A (${CHAIN})" >>"${LOG}"
"${BIN}" \
    --chain "${CHAIN}" \
    --bench-dir "${BENCH_DIR}" \
    --start-block "${START}" \
    --block-count "${COUNT}" \
    --window-size 1000 \
    --skeleton-mode emse \
    --out-dir "${OUT_DIR}" 2>&1 | tee -a "${LOG}"

echo "Stage A ${CHAIN} done. Output: ${OUT_DIR}, log: ${LOG}"
