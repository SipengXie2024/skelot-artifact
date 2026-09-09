# SkelOT artifact

Artifact for the paper *SkelOT: Reusing AOT Compilation Across EVM Contract
Families*, EuroSys 2027, submission 2146.

SkelOT compiles one ahead-of-time artifact per contract *family* instead of one
per code hash. A family is a set of deployed contracts that share the same
skeleton, meaning the same bytecode once PUSH immediates, the Solidity CBOR
metadata trailer, and trailing zeros are stripped. The members differ only in
constants, which the compiler moves into a per-member data table, so one
compiled artifact serves every member of the family.

This artifact contains the prototype, the analysis and figure scripts, the
reference results behind every number in the paper, and instructions for
reproducing them from the four block corpora.

---

## 1. Artifact overview

| Component | What it is | Paper section |
|---|---|---|
| `revmc/crates/revmc/src/emse.rs` | Skeleton extraction, the metadata detector, and byte-verified family grouping | Sections 4 and 5 |
| `revmc/crates/revmc/src/skeleton.rs` | Variance classification and the per-member data table | Section 5 |
| `revmc/crates/revmc/src/compiler/` | Per-member table lowering in the LLVM backend | Section 5 |
| `revmc/crates/revmc-context/` | The runtime context the compiled artifact reads the table through | Section 5 |
| `revmc/examples/runner/` | The measurement harness, eight binaries of which produce paper numbers | Section 6 |
| `scripts/run_stage_a_scan.sh` | Static corpus scan | Table 1, Table 2, Section 6.1, Figure 2 |
| `scripts/run_family_stats.sh` | Grouping, admission guards, family map, nested-frame count, registry sizes | Section 6.1, Section 6.3 |
| `scripts/run_stage_b_compile.sh` | The dual-arm compile benchmark | RQ2, Figure 5, Figure 6 |
| `scripts/run_stage_b_allvariant.sh` | The all-variant arm | Figure 6, Section 7.4 |
| `scripts/run_stage_c_exec.sh` | The correctness gate and the runtime registry | Section 6.3 |
| `scripts/run_stage_replay.sh` | The three replay arms, the per-contract timing file, and the paired comparison | Section 6.3, RQ3, RQ4 |
| `scripts/run_xchain.sh` | PUSH invariance and deployment spans | RQ1, Figure 4, Table 3 |
| `scripts/*.py` | Analysis and figure rendering | Figures 2 and 4 to 8 |
| `data/` | Reference results for every number, with a per-file index in `data/README.md` | all |

The `revmc/` tree is a snapshot of the prototype, which is a fork of
[`paradigmxyz/revmc`](https://github.com/paradigmxyz/revmc).
`revmc/SKELOT-CHANGES.md` separates our research contribution from the upstream
compiler and from bug fixes that happen to live in the same tree, and
`revmc/upstream.diff` is the machine-readable version of that separation.

---

## 2. Environment used for the paper

| | |
|---|---|
| CPU | Intel Xeon Platinum 8275CL at 3.00 GHz, 16 hardware threads |
| Memory | 30 GiB |
| Disk | 968 GB, of which about 60 GB was in use for corpora and caches |
| OS | Ubuntu 24.04.2 LTS (noble), kernel 7.0.0-1009-aws |
| Rust | rustc 1.91 |
| LLVM | 21.1.8 from apt.llvm.org, prefix `/usr/lib/llvm-21` |
| Linker | GNU `ld`, because no bare `lld` was on `PATH` |
| Python | 3.12.3, with matplotlib 3.6.3, numpy 1.26.4 and scipy 1.11.4 |

Two things about this machine matter for reproduction. First, both arms of every
comparison ran on it, at the same thread count, so the comparisons are internally
consistent even where absolute numbers would move on other hardware. Second, the
hardware-counter attribution in Table 5 needs CPU events this machine does not
expose; see Section 9.

---

## 3. Getting started

### Docker

```bash
docker build -t skelot-ae .
docker run --rm -it \
    -v "$PWD":/artifact \
    -v /path/with/room/for/corpora:/bench_data \
    -e BENCH_ROOT=/bench_data \
    skelot-ae
```

The image installs LLVM 21 from apt.llvm.org, Rust 1.91, zstd, jq, and the
Python packages. It deliberately does not create the `/usr/bin/lld` symlink that
upstream revmc's own installer makes, because that switches the linker in both
arms of the comparison. Mount the corpora rather than copying them into the
image. **The Dockerfile has not been built or tested by its author, so treat the
first build as part of the review.**

Hardware performance counters do not work in a default container. The Table 5
measurement is out of scope for the container path; see Section 9.

### Native

```bash
./setup.sh                                     # Ubuntu 24.04, needs sudo
export LLVM_SYS_211_PREFIX=/usr/lib/llvm-21
cd revmc && cargo build --release -p revmc-examples-runner
```

`LLVM_SYS_211_PREFIX` is mandatory rather than optional, because a stock
apt.llvm.org install leaves no unversioned `llvm-config` on `PATH`.
`libpolly-21-dev` is also required, because llvm-21-dev 21.1.8 no longer ships
`libPolly.a`. The build takes about 2 minutes 11 seconds on the machine above.

Every script reads its paths from `scripts/env.sh`, which you can override
entirely from the environment.

| Variable | Default | Meaning |
|---|---|---|
| `ARTIFACT_ROOT` | this directory | Root of the checkout |
| `REVMC_ROOT` | `$ARTIFACT_ROOT/revmc` | The prototype |
| `BENCH_ROOT` | `$ARTIFACT_ROOT/bench_data` | Directory holding `bench_data_base` and friends |
| `RESULTS_ROOT` | `$ARTIFACT_ROOT/results` | Where runs write |
| `CACHE_ROOT` | `$RESULTS_ROOT/caches` | Compiled `.o` and `.so` artifacts |
| `THREADS` | `nproc` | Compile threads, 16 in the paper |

Nothing writes into `data/`, which holds the reference results. The analysis
scripts look in `results/` first and fall back to `data/`, so re-running a
measurement automatically takes precedence over the shipped copy.

### Known test failures

`cargo test -p revmc` reports 618 passed and 10 failed. The ten are the
pre-existing `mload_overflow` cases, which report `MemoryLimitOOG` where the
test expects `MemoryOOG`, instantiated across two backends. They are unrelated
to SkelOT and were failing before this work started. This count is quoted from
the prototype's own record and was not re-measured while assembling the
artifact.

---

## 4. Minimal working example

About ten minutes, of which two are the build.

```bash
./data/fetch_data.sh --smoke base     # ~100 MB, 20 blocks of Base
./scripts/smoke.sh
```

The smoke script builds the runner, groups a 20-block slice of the Base corpus
into families, and then replays one block under the interpreter, Naive per-hash
AOT, and SkelOT, comparing the results.

Expected output, from the same slice on the measurement machine.

| Step | Expect |
|---|---|
| Grouping over 20 blocks (1,718 compilable bytecodes) | about 70 families covering 507 members, 1,211 per-hash units, g1 rejecting 16 skeletons and 51 members, 0 hash-collision splits |
| Single-block replay at block 38,004,930 | 16 families over 61 members, 228 of 228 transactions matching, gas 30886502 reported EQUAL, PASS |

Small drift in the family counts is expected only if you change the block slice.
Given the same slice these are exact counts, not measurements, so they should
match to the digit.

---

## 5. Data

The four corpora are published as zstd-compressed tar archives.

Folder: <https://drive.google.com/open?id=1ykEU7NWj-wlWsgwTMAR6xZiwyf1vCIIx>

| Archive | Compressed | Unpacked, `states/` + `txs/` only | Blocks |
|---|---:|---:|---|
| `bench_data_base.tar.zst` | 2,855,172,343 B | 48 GB | 38,004,930 to 38,014,929 |
| `bench_data_eth.tar.zst` | 1,327,279,648 B | 30 GB | 23,000,000 to 23,009,999 |
| `bench_data_bsc.tar.zst` | 597,255,782 B | 19.4 GB | 95,897,884 to 95,907,883 |
| `bench_data_arb.tar.zst` | 33,804,617 B | 1.25 GB | 458,863,320 to 458,873,319 |

Expected sha256 values are in `data/bench_data.sha256` and are checked before
anything is unpacked.

```bash
BENCH_ROOT=/mnt/big ./data/fetch_data.sh base     # or eth, bsc, arb, all
```

The script downloads with `gdown` or a configured `rclone` remote, verifies the
checksum, and unpacks. You can also download the four files in a browser and
drop them in `$BENCH_ROOT/archives`, in which case the script only verifies and
unpacks.

Two details worth knowing. The archives were written with
`tar --hard-dereference --sort=name | zstd -19 --long=31`, so unpacking needs
`zstd --long=31`; a plain `tar xf` fails with a window-size error on the larger
archives. And **only `states/{block}.bin` and `txs/{block}.bin` are read by any
experiment**. The archives contain the whole original tree, including caches and
logs from unrelated projects, which is why the unpacked sizes above are so much
smaller than the archives' full contents. Pass `FULL_TREE=1` if you want
everything.

---

## 6. Experiment workflow

Ordered. Each step needs everything above it, except where noted. Durations are
what the campaign logs recorded on the machine in Section 2. Peak memory was not
instrumented for any of these runs; the only memory record in the whole project
is from an earlier, 8-thread compile, which peaked at 2,324 MB resident. All
memory figures below are therefore **UNKNOWN** unless stated, with the observation
that no run is known to have come close to exhausting 30 GiB. Two current-boundary
runs were measured with `/usr/bin/time -v`: the paired replay peaked at 1.9 GB
and the Ethereum variance pass at 1.2 GB.

### 6.1 Corpus scan, for Table 1, Table 2, Section 6.1 and Figure 2

```bash
./scripts/run_stage_a_scan.sh base    # and eth, bsc, arb
python3 scripts/check_codehash_consistency_emse.py
python3 scripts/render_fig2_family_distribution.py
```

Input is `states/` for the chain. Output is
`results/<chain>_emse/{dataset_scan.json, skeleton_families.json, skeleton_mapping.tsv}`.
Single-threaded. Base took 922.9 s, Ethereum 886.4 s, BSC 84.5 s, Arbitrum
125.1 s. Output is a few megabytes per chain. RAM UNKNOWN.

The consistency check joins the four `skeleton_mapping.tsv` files and needs all
four scans. It runs in seconds.

### 6.2 Grouping and the family map

```bash
./scripts/run_family_stats.sh grouping
```

Input is `states/`. Output is `results/family_map_emse_base.tsv`, which every
downstream join needs, plus the admission-guard arithmetic and the family-build
timing on stdout. Sub-second for the timed parts, a couple of minutes to read
the corpus. RAM UNKNOWN.

### 6.3 Compile benchmark, for RQ2, Figure 5 and Figure 6

```bash
./scripts/run_stage_b_compile.sh base
./scripts/run_stage_b_compile.sh arb
./scripts/run_stage_b_allvariant.sh
python3 scripts/ablation_817.py
python3 scripts/render_fig5_compile_cost.py
python3 scripts/render_fig6_ablation.py
```

Input is `states/`. Output is
`results/compile_bench_emse_<chain>.json` plus a `.units.jsonl` sibling, and the
compiled artifacts under `$CACHE_ROOT`.

| Run | Wall clock, 16 threads | Cache on disk |
|---|---|---|
| Base, both arms | 11.3 h | 12.4 GB, 58,334 files |
| Arbitrum, both arms | 2.3 h | 2.0 GB |
| All-variant, family subset only | 29 min | 375 MB plus symlinks |

RAM UNKNOWN for all three. The all-variant run needs the Base run's cache,
because it symlinks the 18,440 singleton artifacts and skips them.

The compile cache carries no compiler fingerprint. `cache_hit()` checks only
that a file exists and is non-empty, so a cache built by a different binary is
silently reused, which has been observed to produce a `SIGILL`. Delete the cache
directory rather than resuming into one whose provenance you are unsure of.

The workspace also builds with `panic = "abort"`, so any assertion reachable
from real data kills a multi-hour run with no recovery. Run the smoke test
first.

### 6.4 Correctness gate, for Section 6.3

```bash
./scripts/run_stage_c_exec.sh base
```

Input is `states/`, `txs/`, and both compile caches. Output is
`results/exec_sanity_emse_base.json` and the runtime registry
`results/skeleton_registry_full_emse_base.bin`. About 43 minutes,
single-threaded by design, because the correctness comparison needs a
deterministic per-transaction order. RAM UNKNOWN.

The registry filename is derived from the skeleton and classify modes alone, so
a Base run and an Arbitrum run would otherwise overwrite each other's registry.
The scripts give each chain its own path. This actually happened during the
campaign and cost a run.

### 6.5 Replay arms, for the end-to-end table, RQ3 and RQ4

```bash
./scripts/run_stage_replay.sh arms         # ~40 min total
python3 scripts/family_exec_split.py
./scripts/run_stage_replay.sh allcorpus    # ~14 min, 270 MB of output
python3 scripts/rq4_three_series.py
python3 scripts/render_fig8_coverage_budget.py
./scripts/run_stage_replay.sh paired       # see the RQ3 note in Section 9
python3 scripts/recompute_paired_stats.py
python3 scripts/render_fig7_runtime_speedup.py
```

`arms` runs the same binary three times, once per dispatch mode, and writes
`results/exec_replay_{interpreter,per_hash,skeleton}_base.json`. The individual
runs took 819, 774 and 781 seconds of wall clock.

`allcorpus` adds one more interpreter arm that times every corpus contract
rather than only family members, and writes the per-contract exclusive timing
file. That run took 839 s and its own instrumentation costs about 3% of
execution time.

`paired` is the sampled comparison behind RQ3. It needs `--emit-raw-samples`,
which the script passes, because the statistics are recomputed from the raw
pairs.

### 6.6 Nested frames, for Section 6.3

```bash
./scripts/run_family_stats.sh nested
```

371 s at 16 threads, interpreter-only and untimed by design, so it never touches
a timed path.

### 6.7 Cross-chain measurements, for RQ1, Figure 4 and Table 3

```bash
./scripts/run_xchain.sh base variance     # and eth, bsc, arb
python3 scripts/render_fig4_push_invariance_xchain.py

export ALCHEMY_API_KEY=...                # or RPC_URL=<your archive endpoint>
./scripts/run_xchain.sh base spans        # and eth, bsc, arb
```

The variance pass over Base took 2.6 h single-threaded. Ethereum took 242.6 s
with 1.2 GB peak RSS and Arbitrum 18.2 s with 77 MB (logs
`push_variance_emse_{eth,arb}_20260909*.log`, run through `run_xchain.sh`); the
BSC duration is UNKNOWN because its archived log carries no timestamps.

The deployment-span runs need network access to an archive RPC endpoint, because
they resolve family members back to their deployment blocks. Base took 742.5 s,
Ethereum 590.9 s, BSC 538.3 s and Arbitrum 612.5 s, about 41 minutes for all
four, with zero RPC failures at `--concurrency 12 --rps 12`.

### 6.8 Registry sizes, for Section 6.1 and Section 7.4

```bash
./scripts/run_family_stats.sh registry results/skeleton_registry_full_emse_base.bin
```

Seconds.

### 6.9 Total cost of a full Base reproduction

| Step | Cost |
|---|---|
| Release build | 2 min |
| Corpus scan | 15 min |
| Grouping and family map | minutes |
| Compile benchmark, both arms | 11.3 h, 12.4 GB of cache |
| Correctness gate and registry | 43 min |
| Three replay arms | 40 min |
| All-corpus interpreter timing | 14 min |
| Nested-frame count | 6 min |
| PUSH variance | 2.6 h |
| All-variant compile and its same-day replay pair | 29 min plus 55 min |
| Python analysis and figures | seconds |
| **Total** | **about 17 h** |

Add the other three chains for the cross-chain table, roughly 17 minutes of
scanning, 2.3 h for the Arbitrum compile, and 41 minutes of span resolution.
Peak disk during the Base reproduction is 48 GB of corpus plus 12.4 GB of cache.

---

## 7. Expected results

Each row gives the number as it appears in the paper, the file that carries it,
and the field to read.

### Corpus and families

| Claim | File | Field |
|---|---|---|
| 19,130 unique compilable bytecodes on Base | `base_emse/dataset_scan.json` | `corpus.unique_bytecodes` |
| 10,025 distinct skeletons, 47.60% reduction | same | `corpus.unique_skeletons`, `corpus.reduction_ratio` |
| 825 multi-member families | `base_emse/skeleton_families.json` | count of `families[]` with `family_size > 1` |
| Table 1 rows for Ethereum, BSC, Arbitrum (35,215 / 24,406 / 30.69%, 14,444 / 9,996 / 30.79%, 2,895 / 2,225 / 23.14%) | `{eth,bsc,arb}_10k_emse/dataset_scan.json` | same three fields |
| Table 2 size buckets | `base_emse/dataset_scan.json` | `corpus.buckets` |
| 1,672 code hashes on two or more chains, 145 on all four, 2,970 and 302 at skeleton level | `scripts/check_codehash_consistency_emse.py` | stdout |
| 817 families, 9,220 singletons, 10,037 compile units, g1 rejecting 7 skeletons and 17 members, one family and three members degraded by a static jump | `compile_bench_emse_base_sorted.json` | `records[].grouping` |

### Compile side, RQ2

| Claim | File | Field |
|---|---|---|
| 19,130 units against 10,037, a 47.5% drop | `compile_bench_emse_base_sorted.json` | `records[].n_units` for modes `per_hash` and `skelot` |
| 27,758.3 s against 12,701.5 s, 2.19 times | same | `records[].total_compile_seconds` |
| 5.05 GB against 2.15 GB, a 57.4% drop | same | `records[].total_o_bytes` |
| Arbitrum, 2,895 to 2,227 units, 4,660.3 to 3,612.0 s, 646.0 to 476.9 MB | `compile_bench_emse_arb.json` | same three fields |
| Figure 6 totals, 248,239 s and 3,040.0 MB for Naive AOT, 10,385 s and 141.4 MB for SkelOT, 12,691 s and 168.8 MB all-variant | `ablation_817.json` | `total` |

### Execution side

| Claim | File | Field |
|---|---|---|
| 3,520,323 transactions replayed, byte-identical between modes, zero mismatches | `exec_sanity_emse_base.json` | the two `mode_reports[]` agree exactly on `tx_count`, `success_count` and `total_gas` (458,309,813,705) |
| Exec 534.4 s, 459.1 s and 450.6 s | `exec_replay_{interpreter,per_hash,skeleton}_base.json` | `mode_reports[0].exec_wall_seconds` |
| Family 93.8 s and 84.8 s, Other 365.2 s and 365.8 s | `scripts/family_exec_split.py` | stdout |
| Family build 1.1 s | `run_family_stats.sh grouping` | the 0.78 s grouping and 0.305 s classification lines |
| 3.4 million nested same-family frames | `nested_family_count_emse_base10k_FINAL.json` | `same_family_ancestor_descendant`, 3,395,783 |
| 1,171 faster, 644 equivalent, 27 slower, median 1.31 times | `paired_stats_emse_sampled100_20260909.json` | `summary.verdicts_bh_fdr_q05`, `summary.speedup_median` |

### RQ1, RQ4 and the registry

| Claim | File | Field |
|---|---|---|
| Variant PUSH byte shares 5.08 / 4.11 / 3.09 / 6.28 percent | `logs/push_variance_emse_*.log` | the aggregate lines near the end of each log |
| Table 3 deployment spans | `deployment_spans_emse_{base,eth,bsc,arb}.json` | `families[].deployments[].ts_unix`, span is max minus min over the sample |
| At 75% coverage, 35 SkelOT artifacts against 3,933 members, 112 times fewer artifacts and 437 times less footprint | `rq4_three_series.json` | `rows[]` at `target = 0.75` |
| Registry payload 5.4 MiB over 9,910 members, median table 352 B, file 9.6 MiB | `run_family_stats.sh registry` | stdout, against `skeleton_registry_full_emse.bin` |
| The all-variant registry at 526 MiB | not shipped, see `data/README.md` | file size, 551,704,094 B |
| Table 5 slot attribution | `perf_p1_summary.json` | see Section 9 |

Every number above was checked against the shipped files while this artifact was
assembled, except the two that need a build (the smoke counts and the registry
inspection) and the ones behind Table 5.

---

## 8. Modifications against upstream

`revmc/SKELOT-CHANGES.md` is the full account. In short, the merge base with
`paradigmxyz/revmc` is `4995ac64fb4e564df05b74e645bf0929c0dd5b1f` and the
snapshot is `9acff1288acb046b11cdaf2e5af0aeb20d271e49`. Five source files are new
inside `crates/`, everything else there is an in-place edit, and the whole
compiler-side contribution is roughly 1,900 added lines across nine files. The
rest of the delta is the measurement harness, which upstream did not have.

`revmc/upstream.diff` is the diff over every file that already existed upstream.
`revmc/revmc_fix_pr.md` and `revmc/REVM_API_DIFF.md` are the prototype's own
write-ups of the bug fixes and the revm API migration, which are not part of the
research contribution and are grouped separately in `SKELOT-CHANGES.md`.

---

## 9. Known deviations and caveats

### The paired runtime comparison

The paper's RQ3 numbers (1,842 invoked family members over 99 sampled blocks, 1,171 faster / 644 equivalent / 27 slower after Benjamini-Hochberg correction, median speedup 1.31x with bootstrap 95% CI [1.286, 1.345], median dispatch 23.08 us under Naive AOT against 18.12 us under SkelOT, and the Section 7.1 family-size strata 1.07x / 1.58x) come from `data/paired_emse_base_sampled100_20260909T065454Z.json`, produced by `skeleton_vs_perhash_bench` under the EMSE boundary on the machine in Section 2 with the sorted-schedule compile caches, and recomputed into `data/paired_stats_emse_sampled100_20260909.json` by `scripts/recompute_paired_stats.py`. The run took 2 min 28 s and 1.9 GB peak RSS; its log with the toolchain banner is `data/logs/paired_emse_base_sampled100_20260909T065454Z.log`. An evaluator who runs `run_stage_replay.sh paired` against a freshly built cache and then `recompute_paired_stats.py` should see the same member count and verdict split up to a handful of contracts, and a median in the same range; the absolute microsecond figures depend on the host and are expected to differ.

### The hardware-counter attribution in Table 5

Table 5 reports top-down slot accounting (retiring, bad speculation, frontend bound, backend bound) read around every AOT call with `perf_event_open`. Reproducing it needs a CPU that exposes the top-down slot events (Intel Sapphire Rapids class or newer) and permission to open hardware counters (`perf_event_paranoid` at most 1, or `CAP_PERFMON`); in a container this means running on such a host with `--privileged`. We measured it on a Sapphire Rapids class host; the machine listed in Section 2 does not expose these events. The shipped files `data/perf_p1_summary.json` and `data/perf_frontend_attribution_summary.json` hold the aggregated per-call deltas that Table 5 prints, and `data/perf_frontend_attribution_notes.md` records the event codes and the protocol (repeated paired measurements after warmup; CPU frequency and ASLR not pinned). An evaluator without such a CPU can check that the table rows follow from the summary files but cannot re-measure them; treat Table 5 as an optional, hardware-gated reproduction.

### Figure 2

The paper's Figure 2 has no renderer in any repository; it was produced during
writing and the source was not kept. `scripts/render_fig2_family_distribution.py`
is a new renderer written for this artifact. It reads the same Stage A output and
reproduces the same four log-log rank-size panels, and its printed family counts
match the paper exactly. The callout labels come from the `protocol_tag` field
the scanner records, so they are shorter than the paper's, which came from a
separate on-chain identification pass.

### Figures 4 and 5 carry their numbers inline

`render_fig4_push_invariance_xchain.py` and `render_fig5_compile_cost.py` have
the plotted values written into the script rather than read from a data file.
They are included because they are what produced the figures in the paper, and
the values are the ones in the table in Section 7 above. Changing the underlying
measurement means editing those constants.

### The all-variant comparison must use the same-day pair

The all-variant replay and its control were measured on the same day precisely
because cross-day drift on this machine measures about 21.5 seconds on a
450-second run. The two files
(`exec_replay_allvariant_base.json` and `exec_replay_split_ctrl_20260821.json`)
may be compared with each other and with nothing else. Comparing either against
the three-arm replay from a different date would produce a difference dominated
by drift.

### The all-variant compile run's own totals are not a cold-compile measurement

That run resumes over pre-existing singleton artifacts, and says so in its own
log. Only the 817 family rows of its `.units.jsonl` are used, which is what
`ablation_817.py` reads.

### Two paper scripts were left out on purpose

`build_xchain_tables.py` and `check_codehash_consistency.py` from the paper
repository are not in `scripts/`. Both operate at the previous skeleton
boundary, and `build_xchain_tables.py` writes directly over the camera-ready
`.tex` table files with numbers that no version of the paper reports. Their
current-boundary replacement, `check_codehash_consistency_emse.py`, is included
and produces the numbers the paper prints.

### Stage D no longer exists

The submission-era coverage analysis called a binary named `overlap_analysis`
from a separate repository that is gone. Its output was retired during the
revision and replaced by `scripts/rq4_three_series.py`, which computes the RQ4
series from the per-contract exclusive timing file, the family map, and the
compile record. Those three inputs are all shipped in `data/`.

One of them, `exclusive_per_block_base10k.tsv.zst`, is **provided precomputed
and the tool that produces it is shipped** (`run_stage_replay.sh allcorpus`).
The half-window coverage split in Section 7.4 is derived from the same file by
splitting it at block 38,009,930; that derivation was done offline during the
campaign and has no script in this artifact.

### The compiled-in corpus paths

Six binaries and one helper in the prototype still carry the original author's
absolute corpus paths as clap defaults. Every script here passes `--bench-dir`
explicitly, so they are never used. They were left alone rather than edited
without a build available. `revmc/SKELOT-CHANGES.md` lists them.

### Deleted binaries

29 of the prototype's 47 runner binaries are not in this snapshot. None produced
a paper number; two of them did during submission and were superseded by the
full-corpus ablation. `revmc/SKELOT-CHANGES.md` lists every one and why.

### Exact toolchain patch level

The July and August runs that produced the camera-ready numbers did not write a
version banner. The launch scripts pinned the `1.91` rustup channel, so the
campaign used that channel throughout, but which patch release was in force is
**UNKNOWN**. It was 1.91.0 in April and the channel resolves to 1.91.1 today.
`revmc/rust-toolchain.toml` pins the channel rather than a patch release, which
is the honest reading of what is recorded.

### The linker

revmc probes for a bare `lld` on `PATH` and passes `-fuse-ld=lld` if it finds
one. On the measurement machine only `lld-21` existed, so everything was linked
with GNU `ld`. Upstream's own LLVM installer creates the symlink that flips
this. The Dockerfile and `setup.sh` do not, and `setup.sh` warns if a symlink is
already present.

---

## 10. License

MIT, in `LICENSE`. The prototype under `revmc/` is a fork of `paradigmxyz/revmc`,
which is dual licensed under MIT or Apache-2.0; both upstream license texts stay
in place at `revmc/LICENSE-MIT` and `revmc/LICENSE-APACHE` and continue to apply
to the upstream portions of that tree.
