#!/usr/bin/env bash
# Cross-chain measurements for one chain.
#
#   ./run_xchain.sh base variance     # PUSH-invariance shares, Figure 4 + RQ1
#   ./run_xchain.sh base spans        # deployment spans, Table 3
#
# variance is a static pass over the corpus. Base took 2.6 h single-threaded;
# the smaller chains are proportionally faster. The aggregate lines near the end
# of the log are the numbers Figure 4 plots; the bucket table below them is the
# tiny-versus-huge contrast in Section 6.2.
#
# spans needs network access to an archive RPC endpoint. It resolves a sample of
# each top family's members back to their deployment blocks, so it cannot run
# offline. Each chain took roughly 10 minutes at --concurrency 12 --rps 12; the
# four together took about 41 minutes. Export ALCHEMY_API_KEY, or pass your own
# endpoint through RPC_URL.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

CHAIN="${1:?usage: run_xchain.sh <base|eth|bsc|arb> <variance|spans>}"
WHAT="${2:?usage: run_xchain.sh <base|eth|bsc|arb> <variance|spans>}"
read -r START COUNT <<<"$(chain_window "${CHAIN}")"
BENCH_DIR="$(corpus_dir "${CHAIN}")"
STAMP="$(skelot_stamp)"

case "${WHAT}" in
variance)
    BIN="$(runner_bin push_variance)"
    LOG="${RESULTS_ROOT}/logs/push_variance_emse_${CHAIN}_${STAMP}.log"
    skelot_banner "push_variance (${CHAIN})" >>"${LOG}"
    # --bench-dir is passed explicitly on purpose: without it the binary falls
    # back to a compiled-in corpus table that names the original machine.
    "${BIN}" \
        --chain "${CHAIN}" --skeleton-mode emse \
        --bench-dir "${BENCH_DIR}" \
        --start-block "${START}" --block-count "${COUNT}" 2>&1 | tee -a "${LOG}"
    echo "PUSH variance ${CHAIN} done. Log: ${LOG}"
    ;;
spans)
    BIN="$(runner_bin skeleton_deployment_span)"
    OUT="${RESULTS_ROOT}/deployment_spans_emse_${CHAIN}.json"
    LOG="${RESULTS_ROOT}/logs/deployment_spans_emse_${CHAIN}_${STAMP}.log"
    RPC_ARGS=()
    if [[ -n "${RPC_URL:-}" ]]; then
        RPC_ARGS=(--rpc-url "${RPC_URL}")
    elif [[ -z "${ALCHEMY_API_KEY:-}" ]]; then
        echo "set ALCHEMY_API_KEY, or set RPC_URL to your own archive endpoint" >&2
        exit 1
    fi
    skelot_banner "deployment spans (${CHAIN})" >>"${LOG}"
    "${BIN}" \
        --chain "${CHAIN}" --skeleton-mode emse \
        --bench-dir "${BENCH_DIR}" \
        --start-block "${START}" --block-count "${COUNT}" \
        --top 5 --sample-per-group 30 \
        --concurrency 12 --rps 12 --seed 42 \
        "${RPC_ARGS[@]}" \
        --out "${OUT}" 2>&1 | tee -a "${LOG}"
    echo "Deployment spans ${CHAIN} done. JSON: ${OUT}, log: ${LOG}"
    ;;
*)
    echo "usage: run_xchain.sh <base|eth|bsc|arb> <variance|spans>" >&2
    exit 2
    ;;
esac
