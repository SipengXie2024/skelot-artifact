"""Where the analysis scripts read from and write to.

data/    reference results shipped with the artifact, treated as read-only
results/ everything a run of the artifact produces

`inp` prefers a file you produced over the one we shipped, so the same analysis
script works whether or not you re-ran the measurement that feeds it. Override
ARTIFACT_ROOT, DATA_ROOT or RESULTS_ROOT to move any of it.
"""

import os
import sys
import subprocess
from pathlib import Path

ARTIFACT_ROOT = Path(
    os.environ.get("ARTIFACT_ROOT") or Path(__file__).resolve().parent.parent
)
DATA = Path(os.environ.get("DATA_ROOT") or ARTIFACT_ROOT / "data")
RESULTS = Path(os.environ.get("RESULTS_ROOT") or ARTIFACT_ROOT / "results")


def out(name):
    """Path for something this run produces."""
    p = RESULTS / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# Every path inp() resolved in this process, in order, so an analysis script
# can stamp its output with the inputs it actually read.
RESOLVED = []

# SKELOT_REQUIRE_RESULTS=1 refuses the reference copy under data/ and fails
# when a fresh result is missing from results/.
REQUIRE_RESULTS = os.environ.get("SKELOT_REQUIRE_RESULTS", "") not in ("", "0")


def inp(*names):
    """First of `names` that exists, checked under results/ before data/.

    A name may also be given as a fallback list, e.g. inp("a.tsv", "a.tsv.zst").
    Each resolution is printed to stderr and tagged, so a run that silently
    picked up the shipped reference copy instead of a fresh result is visible.
    """
    roots = (RESULTS,) if REQUIRE_RESULTS else (RESULTS, DATA)
    for root in roots:
        for name in names:
            p = root / name
            if p.exists():
                tag = "REFERENCE copy, not a fresh result" if root == DATA else "fresh result"
                print(f"[paths] {name}: {p} ({tag})", file=sys.stderr)
                RESOLVED.append(p)
                return p
    searched = f"{RESULTS}" if REQUIRE_RESULTS else f"{RESULTS} or {DATA}"
    hint = ("SKELOT_REQUIRE_RESULTS is set, so data/ was not searched. "
            if REQUIRE_RESULTS else "")
    raise FileNotFoundError(
        f"none of {list(names)} found under {searched}. {hint}"
        "Run the measurement that produces it, or check DATA_ROOT/RESULTS_ROOT."
    )


def open_text(path):
    """Open a text file, decompressing on the fly if it ends in .zst.

    The per-contract timing file is 270 MB uncompressed, so the artifact ships
    it compressed. zstd is already required to unpack the corpora.
    """
    path = Path(path)
    if path.suffix != ".zst":
        return open(path)
    proc = subprocess.Popen(
        ["zstd", "-dc", "--long=31", str(path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    return proc.stdout
