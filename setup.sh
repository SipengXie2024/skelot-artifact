#!/usr/bin/env bash
# Native install of everything the artifact needs, on Ubuntu 24.04 (noble).
# The Docker image does the same thing; use this if you would rather not run
# the experiments in a container, which you have to do anyway if you want the
# hardware performance counters.
#
#   ./setup.sh
#
# Needs sudo for the apt steps. Installs rustup under your own home directory.
set -euo pipefail

SUDO=""
[[ "${EUID}" -ne 0 ]] && SUDO="sudo"

echo "==> LLVM 21 repository (apt.llvm.org), not the distro's LLVM 18"
${SUDO} apt-get update
${SUDO} apt-get install -y --no-install-recommends ca-certificates curl gnupg
if [[ ! -f /usr/share/keyrings/apt.llvm.org.gpg ]]; then
    curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        | ${SUDO} gpg --dearmor -o /usr/share/keyrings/apt.llvm.org.gpg
fi
echo "deb [signed-by=/usr/share/keyrings/apt.llvm.org.gpg] https://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" \
    | ${SUDO} tee /etc/apt/sources.list.d/llvm-toolchain-noble-21.list >/dev/null

echo "==> packages"
# libpolly-21-dev is required: llvm-21-dev 21.1.8 no longer ships libPolly.a.
# The python packages are the distro versions that produced the figures,
# matplotlib 3.6.3, numpy 1.26.4 and scipy 1.11.4.
${SUDO} apt-get update
${SUDO} apt-get install -y --no-install-recommends \
    build-essential git pkg-config jq zstd \
    llvm-21 llvm-21-dev llvm-21-runtime llvm-21-tools llvm-21-linker-tools \
    clang-21 clang-tools-21 libclang-common-21-dev libclang-cpp21 \
    libclang1-21 libclang-rt-21-dev libpolly-21-dev lld-21 \
    libzstd-dev \
    python3 python3-matplotlib python3-numpy python3-scipy

# Do NOT symlink lld-21 to /usr/bin/lld. revmc probes for a bare "lld" and
# switches the linker if it finds one; the paper's artifacts were linked with
# GNU ld because no such symlink existed.
if [[ -e /usr/bin/lld ]]; then
    echo "WARNING: /usr/bin/lld exists, so revmc will link with lld rather than" >&2
    echo "         GNU ld. The paper's numbers were measured without it." >&2
fi

echo "==> Rust 1.91"
if ! command -v rustup >/dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --default-toolchain 1.91 --profile minimal
fi
# shellcheck disable=SC1090
. "${HOME}/.cargo/env" 2>/dev/null || true
rustup toolchain install 1.91 --profile minimal

echo "==> cargo git transport"
mkdir -p "${HOME}/.cargo"
if ! grep -q 'git-fetch-with-cli' "${HOME}/.cargo/config.toml" 2>/dev/null; then
    printf '[net]\ngit-fetch-with-cli = true\n' >> "${HOME}/.cargo/config.toml"
fi

echo
echo "Done. Check the environment with:"
echo "  llvm-config-21 --version      # expect 21.1.8"
echo "  rustc +1.91 --version"
echo "  python3 -c 'import matplotlib, numpy, scipy; print(matplotlib.__version__)'"
echo
echo "Then build:"
echo "  export LLVM_SYS_211_PREFIX=/usr/lib/llvm-21"
echo "  (cd revmc && cargo build --release -p revmc-examples-runner)"
