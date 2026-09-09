#!/usr/bin/env bash
# End-to-end replay arms. All of them need run_stage_b_compile.sh and
# run_stage_c_exec.sh to have finished for the same chain and window.
#
#   ./run_stage_replay.sh arms         # three single-arm runs, ~40 min total
#   ./run_stage_replay.sh allcorpus    # per-contract exclusive timing, ~14 min
#   ./run_stage_replay.sh paired       # the sampled paired comparison, RQ3
#
# arms       -> the Exec column of the end-to-end replay table. One run per
#               dispatch mode, single-threaded, so the three numbers are
#               comparable within the same session.
# allcorpus  -> exclusive_per_block.tsv, the per-contract own-time weight file
#               behind Figure 8, the RQ4 ratios and the coverage split. About
#               270 MB of output and roughly 3% slower than the plain
#               interpreter arm because every corpus contract is instrumented.
# paired     -> per-member paired samples with --emit-raw-samples, which is what
#               recompute_paired_stats.py needs. See the artifact README for the
#               provenance of the paired numbers currently in the paper.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

MODE="${1:?usage: run_stage_replay.sh <arms|allcorpus|paired>}"
CHAIN="${CHAIN:-base}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
BIN="$(runner_bin skeleton_vs_perhash_bench)"

CACHE="${CACHE_ROOT}/stage_b_emse_${CHAIN}"
REG="${RESULTS_ROOT}/skeleton_registry_full_emse_${CHAIN}.bin"
STAMP="$(skelot_stamp)"

if [[ ! -f "${REG}" ]]; then
    echo "missing registry ${REG}; run run_stage_c_exec.sh ${CHAIN} first" >&2
    exit 1
fi

common_args=(
    --bench-dir "${BENCH_DIR}"
    --per-hash-cache "${CACHE}/per_hash"
    --skeleton-cache "${CACHE}/skelot_emse"
    --skeleton-mode emse
    --registry "${REG}"
    --start-block "${START}" --block-count "${COUNT}"
)

case "${MODE}" in
arms)
    for arm in interpreter per_hash skeleton; do
        OUT="${RESULTS_ROOT}/exec_replay_${arm}_${CHAIN}.json"
        LOG="${RESULTS_ROOT}/logs/exec_replay_${arm}_${CHAIN}_${STAMP}.log"
        skelot_banner "replay ${arm} (${CHAIN})" >>"${LOG}"
        "${BIN}" "${common_args[@]}" \
            --only-mode "${arm}" \
            --sample-every 1 --rounds 1 --warmup 0 \
            --out "${OUT}" 2>&1 | tee -a "${LOG}"
        echo "${arm}: ${OUT}"
    done
    echo "now run:  python3 ${ARTIFACT_ROOT}/scripts/family_exec_split.py"
    ;;
allcorpus)
    OUT="${RESULTS_ROOT}/exec_replay_interpreter_allcorpus_${CHAIN}.json"
    TSV="${RESULTS_ROOT}/exclusive_per_block_${CHAIN}10k.tsv"
    LOG="${RESULTS_ROOT}/logs/exec_replay_interp_allcorpus_${CHAIN}_${STAMP}.log"
    skelot_banner "replay all-corpus interpreter (${CHAIN})" >>"${LOG}"
    "${BIN}" "${common_args[@]}" \
        --only-mode interpreter --all-corpus-targets \
        --sample-every 1 --rounds 1 --warmup 0 \
        --per-block-out "${TSV}" \
        --out "${OUT}" 2>&1 | tee -a "${LOG}"
    echo "per-contract exclusive timing: ${TSV}"
    ;;
paired)
    OUT="${RESULTS_ROOT}/skeleton_vs_perhash_${CHAIN}.json"
    LOG="${RESULTS_ROOT}/logs/paired_${CHAIN}_${STAMP}.log"
    skelot_banner "paired sampled replay (${CHAIN})" >>"${LOG}"
    "${BIN}" "${common_args[@]}" \
        --only-mode both \
        --sample-every 100 --rounds 5 --warmup 2 \
        --emit-raw-samples \
        --out "${OUT}" 2>&1 | tee -a "${LOG}"
    echo "paired samples: ${OUT}"
    echo "now run:  python3 ${ARTIFACT_ROOT}/scripts/recompute_paired_stats.py ${OUT} ${RESULTS_ROOT}/paired_stats_recomputed.json"
    ;;
*)
    echo "usage: run_stage_replay.sh <arms|allcorpus|paired>" >&2
    exit 2
    ;;
esac
