#!/usr/bin/env bash
# Shared configuration for every SkelOT artifact script.
#
#   . "$(dirname "${BASH_SOURCE[0]}")/env.sh"
#
# Everything below can be overridden by exporting the variable before the call.
# No path in this artifact is hardcoded to the machine the paper was measured on.

# Root of this artifact checkout.
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# The prototype snapshot. Change this to point at your own checkout of revmc.
REVMC_ROOT="${REVMC_ROOT:-${ARTIFACT_ROOT}/revmc}"

# Directory that holds bench_data_base, bench_data_eth, bench_data_bsc and
# bench_data_arb. data/fetch_data.sh extracts into exactly this layout.
BENCH_ROOT="${BENCH_ROOT:-${ARTIFACT_ROOT}/bench_data}"

# Everything a run produces goes here. Nothing writes into data/, which holds
# the reference results shipped with the artifact.
RESULTS_ROOT="${RESULTS_ROOT:-${ARTIFACT_ROOT}/results}"

# Compiled .o and .so artifacts. Budget 12.4 GB for a full Base compile.
CACHE_ROOT="${CACHE_ROOT:-${RESULTS_ROOT}/caches}"

# Compile threads. The paper used 16.
THREADS="${THREADS:-$(nproc)}"

# llvm-sys finds LLVM through this variable. There is no unversioned
# llvm-config on a stock apt.llvm.org install, so it is mandatory.
LLVM_SYS_211_PREFIX="${LLVM_SYS_211_PREFIX:-/usr/lib/llvm-21}"
export LLVM_SYS_211_PREFIX
export PATH="${LLVM_SYS_211_PREFIX}/bin:${HOME}/.cargo/bin:${PATH}"

export ARTIFACT_ROOT REVMC_ROOT BENCH_ROOT RESULTS_ROOT CACHE_ROOT THREADS

mkdir -p "${RESULTS_ROOT}" "${RESULTS_ROOT}/logs"

# Absolute path of a release binary from the runner package. Fails with a build
# hint rather than a confusing "No such file or directory" deep in a driver.
runner_bin() {
    local name="$1" path="${REVMC_ROOT}/target/release/$1"
    if [[ ! -x "${path}" ]]; then
        echo "missing ${path}" >&2
        echo "build it first:  (cd ${REVMC_ROOT} && cargo build --release -p revmc-examples-runner)" >&2
        return 1
    fi
    printf '%s' "${path}"
}

# Corpus directory for a chain, checked for the two subdirectories every
# experiment reads.
corpus_dir() {
    local chain="$1" dir="${BENCH_ROOT}/bench_data_$1"
    if [[ ! -d "${dir}/states" || ! -d "${dir}/txs" ]]; then
        echo "corpus ${dir} is missing states/ or txs/" >&2
        echo "fetch it first:  BENCH_ROOT=${BENCH_ROOT} ${ARTIFACT_ROOT}/data/fetch_data.sh $1" >&2
        return 1
    fi
    printf '%s' "${dir}"
}

# Provenance header. Every log starts with one, so a result can always be tied
# back to a tree state and a toolchain.
skelot_banner() {
    local stage="$1"
    local sha="unknown"
    if git -C "${REVMC_ROOT}" rev-parse HEAD >/dev/null 2>&1; then
        sha="$(git -C "${REVMC_ROOT}" rev-parse HEAD)"
        [[ -n "$(git -C "${REVMC_ROOT}" status --porcelain)" ]] && sha="${sha}-dirty"
    fi
    echo "# ${stage} run $(date -u +%Y%m%dT%H%M%SZ)"
    echo "revmc_sha: ${sha}"
    echo "rustc: $(rustc --version 2>&1)"
    echo "llvm: $(llvm-config-21 --version 2>/dev/null || llvm-config --version 2>/dev/null || echo unknown)"
    echo "threads: ${THREADS}"
    echo "bench_root: ${BENCH_ROOT}"
    echo "uname: $(uname -a)"
    lscpu 2>/dev/null | head -6
    echo "---"
}

# UTC stamp used in log file names.
skelot_stamp() { date -u +%Y%m%dT%H%M%SZ; }

# The block window each chain's numbers were measured over, as
# "<start-block> <block-count>". Table 1 and every downstream aggregation
# assume exactly these windows.
chain_window() {
    case "$1" in
        base) echo "38004930 10000" ;;
        eth)  echo "23000000 10000" ;;
        bsc)  echo "95897884 10000" ;;
        arb)  echo "458863320 10000" ;;
        *)    echo "unknown chain '$1' (expected base|eth|bsc|arb)" >&2; return 1 ;;
    esac
}
