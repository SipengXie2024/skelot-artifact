#!/usr/bin/env bash
# The all-variant arm: one shared artifact per family with every constant in the
# table, instead of the invariant/variant split. Figure 6's third bar and the
# Section 7.4 comparison.
#
#   ./run_stage_b_allvariant.sh          # ~29 min at 16 threads
#
# Restricted to the 817 shared families on purpose. Singleton units are
# byte-identical under both designs, so they are symlinked in from the split
# cache and skipped by --resume; only the family rows of the .units.jsonl are
# used downstream. The run therefore needs run_stage_b_compile.sh base to have
# finished first.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN=base
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
BIN="$(runner_bin skelot_compile_bench)"

SRC="${CACHE_ROOT}/stage_b_emse_base/skelot_emse"
CACHE="${CACHE_ROOT}/stage_b_emse_base_allvariant"
DST="${CACHE}/skelot_emse_forced"
OUT="${RESULTS_ROOT}/compile_bench_emse_base_allvariant.json"
LOG="${RESULTS_ROOT}/logs/allvariant_compile_$(skelot_stamp).log"

if [[ ! -d "${SRC}" ]]; then
    echo "missing split cache ${SRC}; run run_stage_b_compile.sh base first" >&2
    exit 1
fi

echo "[1/2] symlinking singleton artifacts from the split cache"
mkdir -p "${DST}"
n=0
for f in "${SRC}"/*; do
    b="${f##*/}"
    case "${b}" in skel_*) continue ;; esac
    ln -sf "${f}" "${DST}/${b}"
    n=$((n + 1))
done
echo "linked ${n} files"
if [[ "${n}" -ne 18440 ]]; then
    echo "ABORT: expected 18440 singleton links (9,220 units x .o/.so), got ${n}" >&2
    echo "the split cache is incomplete or was built over a different window" >&2
    exit 1
fi

echo "[2/2] all-variant family-subset compile"
skelot_banner "Stage B all-variant" >>"${LOG}"
"${BIN}" \
    --bench-dir "${BENCH_DIR}" \
    --start-block "${START}" --block-count "${COUNT}" \
    --mode skeleton --skeleton-mode emse \
    --classify-mode force-all-variant \
    --scope full_10k_emse_allvariant \
    --cache-dir "${CACHE}" \
    --threads "${THREADS}" --resume \
    --out "${OUT}" 2>&1 | tee -a "${LOG}"

echo "All-variant compile done. JSON: ${OUT}, log: ${LOG}"
echo "Note: the run's own totals are not a cold-compile measurement, because"
echo "--resume skipped the pre-existing singleton units. Only the 817 family"
echo "rows in ${OUT}.units.jsonl are used."
