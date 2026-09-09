"""Where the analysis scripts read from and write to.

data/    reference results shipped with the artifact, treated as read-only
results/ everything a run of the artifact produces

`inp` prefers a file you produced over the one we shipped, so the same analysis
script works whether or not you re-ran the measurement that feeds it. Override
ARTIFACT_ROOT, DATA_ROOT or RESULTS_ROOT to move any of it.
"""

import os
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


def inp(*names):
    """First of `names` that exists, checked under results/ before data/.

    A name may also be given as a fallback list, e.g. inp("a.tsv", "a.tsv.zst").
    """
    for root in (RESULTS, DATA):
        for name in names:
            p = root / name
            if p.exists():
                return p
    raise FileNotFoundError(
        f"none of {list(names)} found under {RESULTS} or {DATA}. "
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
