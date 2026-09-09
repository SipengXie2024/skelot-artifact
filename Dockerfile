# Build environment for the SkelOT artifact.
#
#   docker build -t skelot-ae .
#   docker run --rm -it \
#       -v "$PWD":/artifact \
#       -v /path/to/corpora:/bench_data \
#       -e BENCH_ROOT=/bench_data \
#       skelot-ae
#
# Mount the corpora rather than copying them in: Base alone is 48 GB of states
# and transactions, and a full compile writes another 12.4 GB of object cache.
# Reserve at least 80 GB of container-visible disk and 30 GB of RAM for a
# 16-thread compile.
#
# This image has not been built or tested by the person who wrote it. Treat the
# first build as part of the review.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# LLVM 21 comes from apt.llvm.org, not from the distro, which ships LLVM 18.
# The repository line is the same one that was in force on the measurement
# machine.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg && \
    curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        | gpg --dearmor -o /usr/share/keyrings/apt.llvm.org.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/apt.llvm.org.gpg] https://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" \
        > /etc/apt/sources.list.d/llvm-toolchain-noble-21.list && \
    rm -rf /var/lib/apt/lists/*

# libpolly-21-dev is not optional: llvm-21-dev 21.1.8 no longer ships
# libPolly.a, which llvm-sys links.
# Deliberately absent: a /usr/bin/lld symlink. Upstream revmc's own installer
# creates one, which flips the linker from GNU ld to lld in both arms of the
# comparison. Every artifact behind the paper's numbers was linked with GNU ld.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git pkg-config jq zstd \
        llvm-21 llvm-21-dev llvm-21-runtime llvm-21-tools llvm-21-linker-tools \
        clang-21 clang-tools-21 libclang-common-21-dev libclang-cpp21 \
        libclang1-21 libclang-rt-21-dev libpolly-21-dev lld-21 \
        libzstd-dev \
        python3 python3-matplotlib python3-numpy python3-scipy && \
    rm -rf /var/lib/apt/lists/*

# The distro python packages are exactly the versions that produced the
# figures: matplotlib 3.6.3, numpy 1.26.4, scipy 1.11.4. Installing them from
# pip would drift, and Ubuntu 24.04 refuses a system-wide pip install anyway.

ENV LLVM_SYS_211_PREFIX=/usr/lib/llvm-21
ENV PATH=/usr/lib/llvm-21/bin:/root/.cargo/bin:$PATH
ENV RUSTUP_HOME=/root/.rustup CARGO_HOME=/root/.cargo

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --default-toolchain 1.91 --profile minimal && \
    rustc --version && cargo --version

# Cargo resolves the revm dependency over git. On the measurement machine this
# setting lived in the user's global config and was invisible to a fresh clone.
RUN mkdir -p /root/.cargo && \
    printf '[net]\ngit-fetch-with-cli = true\n' >> /root/.cargo/config.toml

WORKDIR /artifact
ENV ARTIFACT_ROOT=/artifact
ENV BENCH_ROOT=/bench_data

CMD ["/bin/bash"]
