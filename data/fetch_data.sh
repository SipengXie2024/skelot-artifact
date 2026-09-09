#!/usr/bin/env bash
# Download, verify and unpack the four block corpora.
#
#   ./fetch_data.sh base            # states/ and txs/ for Base, ~48 GB unpacked
#   ./fetch_data.sh all             # all four chains, ~99 GB unpacked
#   ./fetch_data.sh --smoke base    # only the 20 blocks the smoke test needs
#   FULL_TREE=1 ./fetch_data.sh base    # the whole archived tree, 83 GB
#
# Environment:
#   BENCH_ROOT    where the corpora land. Default $ARTIFACT_ROOT/bench_data.
#   ARCHIVE_DIR   where the .tar.zst files are kept. Default $BENCH_ROOT/archives.
#
# Only two subdirectories of each corpus are read by any experiment,
# states/{block}.bin and txs/{block}.bin, so that is all this script unpacks
# unless you ask for FULL_TREE=1. The archives themselves contain the whole
# original tree, including caches and logs from unrelated projects.
#
# The archives live in this Google Drive folder:
#
#   https://drive.google.com/open?id=1ykEU7NWj-wlWsgwTMAR6xZiwyf1vCIIx
#
#   bench_data_base.tar.zst   2,855,172,343 bytes
#   bench_data_eth.tar.zst    1,327,279,648 bytes
#   bench_data_bsc.tar.zst      597,255,782 bytes
#   bench_data_arb.tar.zst       33,804,617 bytes
#
# with a .sha256 and a .list.txt beside each one. Expected sha256 values are in
# bench_data.sha256 next to this script and are checked before any extraction.
#
# The script downloads with gdown (pip install gdown) or, if you have a remote
# configured for the folder, with rclone. Both fetch the whole folder; there is
# no per-file link. You can also download the four files by hand in a browser
# and drop them into ARCHIVE_DIR, in which case this script only verifies and
# unpacks.
#
# The archives were written with
#   tar --hard-dereference --sort=name ... | zstd -19 --long=31
# so unpacking needs "zstd --long=31". A plain "tar xf" without the long-window
# flag fails with a window-size error on the larger archives.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$(cd "${HERE}/.." && pwd)}"
BENCH_ROOT="${BENCH_ROOT:-${ARTIFACT_ROOT}/bench_data}"
ARCHIVE_DIR="${ARCHIVE_DIR:-${BENCH_ROOT}/archives}"
FOLDER_URL="https://drive.google.com/open?id=1ykEU7NWj-wlWsgwTMAR6xZiwyf1vCIIx"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"   # e.g. "migration_drive:bench-data-archive-20260701"

SMOKE=0
if [[ "${1:-}" == "--smoke" ]]; then SMOKE=1; shift; fi
WHICH="${1:?usage: fetch_data.sh [--smoke] <base|eth|bsc|arb|all>}"

case "${WHICH}" in
    all) CHAINS=(base eth bsc arb) ;;
    base|eth|bsc|arb) CHAINS=("${WHICH}") ;;
    *) echo "unknown corpus '${WHICH}'" >&2; exit 2 ;;
esac

command -v zstd >/dev/null || { echo "zstd is required (apt install zstd)" >&2; exit 1; }
mkdir -p "${ARCHIVE_DIR}" "${BENCH_ROOT}"

download_folder() {
    local missing=0
    for c in "${CHAINS[@]}"; do
        [[ -f "${ARCHIVE_DIR}/bench_data_${c}.tar.zst" ]] || missing=1
    done
    [[ "${missing}" -eq 0 ]] && return 0

    if [[ -n "${RCLONE_REMOTE}" ]] && command -v rclone >/dev/null; then
        echo "==> rclone copy ${RCLONE_REMOTE} -> ${ARCHIVE_DIR}"
        for c in "${CHAINS[@]}"; do
            rclone copy "${RCLONE_REMOTE}/bench_data_${c}.tar.zst" "${ARCHIVE_DIR}/" --progress
        done
    elif command -v gdown >/dev/null; then
        echo "==> gdown --folder ${FOLDER_URL} -> ${ARCHIVE_DIR}"
        echo "    (this fetches every archive in the folder, about 4.8 GB)"
        gdown --folder "${FOLDER_URL}" -O "${ARCHIVE_DIR}" --remaining-ok
        # gdown puts the folder's contents in a subdirectory named after it.
        find "${ARCHIVE_DIR}" -mindepth 2 -maxdepth 2 -name 'bench_data_*' \
            -exec mv -n {} "${ARCHIVE_DIR}/" \;
    else
        echo "neither gdown nor a configured rclone remote is available." >&2
        echo "Install gdown (pip install gdown), or set RCLONE_REMOTE, or" >&2
        echo "download the archives by hand from" >&2
        echo "  ${FOLDER_URL}" >&2
        echo "into ${ARCHIVE_DIR} and re-run." >&2
        exit 1
    fi
}

verify() {
    local c="$1" archive="${ARCHIVE_DIR}/bench_data_${c}.tar.zst"
    [[ -f "${archive}" ]] || { echo "missing ${archive}" >&2; exit 1; }
    local want
    want="$(awk -v f="bench_data_${c}.tar.zst" '$2 == f {print $1}' "${HERE}/bench_data.sha256")"
    [[ -n "${want}" ]] || { echo "no expected sha256 for ${c}" >&2; exit 1; }
    echo "==> sha256 ${c} (this reads the whole archive)"
    local got
    got="$(sha256sum "${archive}" | awk '{print $1}')"
    if [[ "${got}" != "${want}" ]]; then
        echo "CHECKSUM MISMATCH for bench_data_${c}.tar.zst" >&2
        echo "  expected ${want}" >&2
        echo "  got      ${got}" >&2
        exit 1
    fi
    echo "    ok"
}

members() {
    local c="$1"
    if [[ "${FULL_TREE:-0}" == "1" ]]; then
        return 0            # no member list: extract everything
    fi
    printf '%s\n' "bench_data_${c}/states" "bench_data_${c}/txs"
    # Base predates the manifest; the other three carry one and
    # skelot_dataset_scan records its schema version in its output.
    [[ "${c}" != "base" ]] && printf '%s\n' "bench_data_${c}/manifest.json"
    return 0
}

smoke_members() {
    local c="$1" start="$2" n=20
    local b
    for ((b = start; b < start + n; b++)); do
        printf '%s\n' "bench_data_${c}/states/${b}.bin" "bench_data_${c}/txs/${b}.bin"
    done
}

start_block_of() {
    case "$1" in
        base) echo 38004930 ;;
        eth)  echo 23000000 ;;
        bsc)  echo 95897884 ;;
        arb)  echo 458863320 ;;
    esac
}

download_folder
for c in "${CHAINS[@]}"; do
    verify "${c}"
    archive="${ARCHIVE_DIR}/bench_data_${c}.tar.zst"
    mapfile -t sel < <(if [[ "${SMOKE}" -eq 1 ]]; then smoke_members "${c}" "$(start_block_of "${c}")"; else members "${c}"; fi)
    echo "==> unpacking bench_data_${c} into ${BENCH_ROOT}"
    if [[ "${#sel[@]}" -eq 0 ]]; then
        tar --use-compress-program='zstd -d --long=31' -xf "${archive}" -C "${BENCH_ROOT}"
    else
        tar --use-compress-program='zstd -d --long=31' -xf "${archive}" -C "${BENCH_ROOT}" "${sel[@]}"
    fi
    echo "    $(du -sh "${BENCH_ROOT}/bench_data_${c}" | cut -f1) in ${BENCH_ROOT}/bench_data_${c}"
done

echo
echo "Corpora ready under ${BENCH_ROOT}. Point the experiment scripts at it with"
echo "  export BENCH_ROOT=${BENCH_ROOT}"
