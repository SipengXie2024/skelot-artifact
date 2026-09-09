#!/usr/bin/env bash
# Family grouping, the family map, the nested-frame count, and registry sizes.
#
#   ./run_family_stats.sh                 # grouping + family map + timing
#   ./run_family_stats.sh nested          # add the nested-frame replay (~6 min)
#   ./run_family_stats.sh registry PATH   # report sizes of a saved registry
#
# grouping_stats prints the admission-guard arithmetic (817 families, 9,220
# singletons, 10,037 compile units on Base) and the family-build timing that the
# end-to-end replay table reports as 1.1 s. It also writes family_map.tsv, which
# the ablation, RQ4 and the family/other split all join against.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

MODE="${1:-grouping}"
CHAIN="${CHAIN:-base}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"

case "${MODE}" in
grouping)
    BENCH_DIR="$(corpus_dir "${CHAIN}")"
    BIN="$(runner_bin grouping_stats)"
    MAP="${RESULTS_ROOT}/family_map_emse_${CHAIN}.tsv"
    LOG="${RESULTS_ROOT}/logs/grouping_${CHAIN}_$(skelot_stamp).log"
    skelot_banner "grouping_stats (${CHAIN})" >>"${LOG}"
    "${BIN}" \
        --bench-dir "${BENCH_DIR}" \
        --start-block "${START}" --block-count "${COUNT}" \
        --skeleton-mode emse \
        --time-analysis \
        --export-family-map "${MAP}" 2>&1 | tee -a "${LOG}"
    echo "family map: ${MAP}"
    ;;
nested)
    BENCH_DIR="$(corpus_dir "${CHAIN}")"
    BIN="$(runner_bin nested_family_count)"
    OUT="${RESULTS_ROOT}/nested_family_count_emse_${CHAIN}10k.json"
    LOG="${RESULTS_ROOT}/logs/nested_${CHAIN}_$(skelot_stamp).log"
    skelot_banner "nested_family_count (${CHAIN})" >>"${LOG}"
    "${BIN}" \
        --bench-dir "${BENCH_DIR}" \
        --start-block "${START}" --block-count "${COUNT}" \
        --threads "${THREADS}" --skeleton-mode emse \
        --out "${OUT}" 2>&1 | tee -a "${LOG}"
    echo "nested counts: ${OUT}"
    ;;
registry)
    REG="${2:?usage: run_family_stats.sh registry <path to skeleton_registry_full_emse.bin>}"
    "$(runner_bin inspect_registry)" "${REG}"
    ;;
*)
    echo "usage: run_family_stats.sh [grouping|nested|registry <path>]" >&2
    exit 2
    ;;
esac
