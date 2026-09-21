#!/usr/bin/env bash
# Stage C: the correctness gate. Replays every transaction in the window under
# both dispatch modes and compares the results byte for byte.
#
#   ./run_stage_c_exec.sh base        # ~43 min, single-threaded by design
#   ./run_stage_c_exec.sh arb         # ~1 min
#
# On Base this is the run behind "9,997 non-empty blocks, 3.52M transactions,
# zero mismatches". It also builds and saves the runtime family registry that
# every later replay loads, so run it before run_stage_replay.sh.
#
# Registry handling: --registry is read-only for the driver, so it is passed
# only when the per-chain file already exists. On a first run the driver builds
# the registry itself and saves it next to --out under the fixed name
# skeleton_registry_full_emse.bin, derived from the skeleton and classify modes
# alone, so a Base run and an Arbitrum run would otherwise overwrite each
# other's file. This script renames it to the per-chain path that
# run_stage_replay.sh reads.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN="${1:?usage: run_stage_c_exec.sh <base|arb|eth|bsc>}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
BIN="$(runner_bin skeleton_vs_perhash_bench)"

CACHE="${CACHE_ROOT}/stage_b_emse_${CHAIN}"
OUT="${RESULTS_ROOT}/exec_sanity_emse_${CHAIN}.json"
REG="${RESULTS_ROOT}/skeleton_registry_full_emse_${CHAIN}.bin"
LOG="${RESULTS_ROOT}/logs/exec_sanity_emse_${CHAIN}_$(skelot_stamp).log"

if [[ ! -d "${CACHE}/per_hash" || ! -d "${CACHE}/skelot_emse" ]]; then
    echo "missing compiled artifacts under ${CACHE}" >&2
    echo "run run_stage_b_compile.sh ${CHAIN} first" >&2
    exit 1
fi

# Where the driver saves the registry when it builds one itself (next to --out).
REG_BUILT="$(dirname "${OUT}")/skeleton_registry_full_emse.bin"
REG_FLAG=()
if [[ -f "${REG}" ]]; then
    REG_FLAG=(--registry "${REG}")
else
    echo "no registry at ${REG}; the driver builds one during this run" | tee -a "${LOG}"
fi

skelot_banner "Stage C (${CHAIN})" >>"${LOG}"
"${BIN}" \
    --bench-dir "${BENCH_DIR}" \
    --per-hash-cache "${CACHE}/per_hash" \
    --skeleton-cache "${CACHE}/skelot_emse" \
    --skeleton-mode emse --only-mode both \
    --start-block "${START}" --block-count "${COUNT}" \
    --sample-every 1 --rounds 1 --warmup 0 \
    "${REG_FLAG[@]}" \
    --out "${OUT}" 2>&1 | tee -a "${LOG}"

if [[ ! -f "${REG}" ]]; then
    if [[ ! -f "${REG_BUILT}" ]]; then
        echo "driver finished but left no registry at ${REG_BUILT}" >&2
        exit 1
    fi
    mv "${REG_BUILT}" "${REG}"
    echo "registry saved as ${REG}" | tee -a "${LOG}"
fi

echo "Stage C ${CHAIN} done. JSON: ${OUT}, registry: ${REG}, log: ${LOG}"
