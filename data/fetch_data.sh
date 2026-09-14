#!/usr/bin/env bash
# Download, verify and unpack the four block corpora.
#
#   ./fetch_data.sh base            # states/ and txs/ for Base, ~48 GB unpacked
#   ./fetch_data.sh all             # all four chains, ~99 GB unpacked
#   ./fetch_data.sh --smoke base    # 6 MB download, the 20 blocks the smoke test needs (87 MB unpacked)
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
# The script downloads each archive by its Drive file id with gdown (installed by
# setup.sh and the Dockerfile) or, if you have a remote configured for the folder,
# with rclone, or from the Zenodo dataset (set USE_ZENODO=1 to prefer it).
# Only the archives you ask for are fetched; there is
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

# Google Drive file ids inside the shared folder (rclone lsjson, 2026-09-14).
drive_id() {
    case "$1" in
        base)    echo 1__uy69r6laQCSgdJ5SAPnEsUMXl-m04k ;;
        eth)     echo 1y_yYMegsJ8Cipck0XprtcgExAOAJBo68 ;;
        bsc)     echo 16FM-h_dZAvdCEdclYsUYiP4Ge9Yh-qn- ;;
        arb)     echo 1LZXkJyGspYnqH1_udH0qaSSCt7adbzKf ;;
        smoke20) echo 13HQImDrcHgOC1YVegH7e99Q1HOtFw0Mo ;;
    esac
}

fetch_one() {
    local name="$1" id="$2"
    local dst="${ARCHIVE_DIR}/${name}"
    [[ -f "${dst}" ]] && return 0
    if [[ -n "${RCLONE_REMOTE}" ]] && command -v rclone >/dev/null; then
        echo "==> rclone copy ${RCLONE_REMOTE}/${name} -> ${ARCHIVE_DIR}"
        rclone copy "${RCLONE_REMOTE}/${name}" "${ARCHIVE_DIR}/" --progress
    elif command -v gdown >/dev/null && [[ -z "${USE_ZENODO:-}" ]]; then
        echo "==> gdown ${name} (Drive id ${id}) -> ${ARCHIVE_DIR}"
        gdown "https://drive.google.com/uc?id=${id}" -O "${dst}"
    elif command -v curl >/dev/null; then
        # Permanent copy: Zenodo record 10.5281/zenodo.22740636. Slower than Drive.
        echo "==> curl ${name} from Zenodo -> ${ARCHIVE_DIR}"
        curl -L --fail --retry 3 -o "${dst}" "https://zenodo.org/records/22740636/files/${name}?download=1"
    else
        echo "neither gdown nor a configured rclone remote is available." >&2
        echo "setup.sh and the Dockerfile install gdown; otherwise" >&2
        echo "  python3 -m pip install --break-system-packages 'gdown>=5.2'" >&2
        echo "or download ${name} by hand from" >&2
        echo "  ${FOLDER_URL}" >&2
        echo "into ${ARCHIVE_DIR} and re-run." >&2
        exit 1
    fi
}

download_archives() {
    if [[ "${SMOKE}" -eq 1 ]]; then
        fetch_one bench_data_base_smoke20.tar.zst "$(drive_id smoke20)"
        return 0
    fi
    for c in "${CHAINS[@]}"; do
        fetch_one "bench_data_${c}.tar.zst" "$(drive_id "${c}")"
    done
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

download_archives

if [[ "${SMOKE}" -eq 1 ]]; then
    # The smoke archive holds only blocks 38004930..38004949 of Base (states and
    # txs, 87 MB unpacked); unpack it whole.
    name=bench_data_base_smoke20.tar.zst
    want="$(awk -v f="${name}" '$2 == f {print $1}' "${HERE}/bench_data.sha256")"
    got="$(sha256sum "${ARCHIVE_DIR}/${name}" | awk '{print $1}')"
    [[ "${got}" == "${want}" ]] || { echo "sha256 mismatch for ${name}: got ${got}, want ${want}" >&2; exit 1; }
    echo "==> unpacking the 20-block smoke slice into ${BENCH_ROOT}"
    tar --use-compress-program='zstd -d --long=31' -xf "${ARCHIVE_DIR}/${name}" -C "${BENCH_ROOT}"
    echo "    $(du -sh "${BENCH_ROOT}/bench_data_base" | cut -f1) in ${BENCH_ROOT}/bench_data_base"
    echo "Smoke slice ready. export BENCH_ROOT=${BENCH_ROOT}"
    exit 0
fi

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
