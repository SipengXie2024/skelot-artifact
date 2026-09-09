# What SkelOT changed in revmc

This tree is a snapshot of the SkelOT prototype, which is a fork of
[`paradigmxyz/revmc`](https://github.com/paradigmxyz/revmc). This file separates
our research contribution from the upstream compiler and from bug fixes that
happen to live in the same tree.

## Provenance

| | |
|---|---|
| Upstream project | `paradigmxyz/revmc` |
| Upstream base commit (merge base) | `4995ac64fb4e564df05b74e645bf0929c0dd5b1f` (2026-01-23) |
| Snapshot commit of the SkelOT prototype | `9acff1288acb046b11cdaf2e5af0aeb20d271e49`, branch `jit-integration` (2026-08-02) |
| Range statistics | 137 files changed, 45,174 insertions, 887 deletions over 181 commits |
| Machine-readable diff | `upstream.diff` in this directory |

`upstream.diff` is the output of

```bash
git diff 4995ac64fb4e564df05b74e645bf0929c0dd5b1f..9acff1288acb046b11cdaf2e5af0aeb20d271e49 \
    -- crates/ Cargo.toml examples/runner/Cargo.toml examples/runner/build.rs \
       examples/runner/src/common.rs examples/runner/src/lib.rs examples/runner/src/main.rs \
       tests/state-tests/ scripts/
```

It covers every file that already existed upstream, which is the whole
compiler-side story. It deliberately does not cover `examples/runner/src/bin/`,
`examples/runner/src/` beyond the three upstream files, or `docs/`: upstream had
no `docs/` directory at all and `examples/runner/` contained exactly five files
(`Cargo.toml`, `build.rs`, `src/common.rs`, `src/lib.rs`, `src/main.rs`), so
everything else under those paths is ours and a diff would just be the file
itself.

Only five source files are new inside `crates/`: `emse.rs`, `profile.rs`,
`skeleton.rs`, `skeleton_admission.rs`, and `tests/smod_zero_opaque.rs`.
Everything else in `crates/` is an in-place edit. The whole compiler-side
contribution is roughly 1,900 added lines across nine files; the rest of the
45k lines are the measurement harness under `examples/runner/`, the engineering
record under `docs/`, and `Cargo.lock`.

## Group A — Skeleton extraction and the EMSE-Style boundary

| File | What it does |
|---|---|
| `crates/revmc/src/emse.rs` (new, 635 lines) | The EMSE-Style boundary. `extract_emse_skeleton` / `strip_emse_suffixes` strip PUSH immediates, the Solidity CBOR metadata trailer, and trailing zeros. `strip_solidity_cbor_metadata`, `looks_like_solidity_cbor_metadata`, and `cbor_text_key_appears` implement the metadata detector. `group_skeleton_families` is the byte-verified family grouping: hash bucket first, then full skeleton-byte equality, so a hash collision splits a family instead of merging two. `SkeletonMode` selects the boundary; `GroupingStats`, `SkeletonFamily`, and `SkeletonGrouping` are the output types. |
| `crates/revmc/src/skeleton.rs` (new, 496 lines) | `extract_opcode_skeleton` (the plain PUSH-immediate skeleton) and `extract_push_immediates`. Also hosts the variance types, see Group B. |
| `crates/revmc/src/lib.rs` | Four added lines exporting the new modules. |

The module doc comment at the top of `emse.rs` states the contract that callers
must strip before running variance analysis or building data tables, because
members of one EMSE family may have different raw lengths.

## Group B — Variance classification and the family registry

| File | What it does |
|---|---|
| `crates/revmc/src/skeleton.rs` | `PushClassification` (`Invariant` / `Variant { table_index }`), `SkeletonVariance`, `ImmDataTable`, `ClassifyMode`. `analyze_skeleton_group{,_with_mode}` classifies each PUSH site across a family's members; `build_data_table` emits the per-member table of 32-byte entries; `skip_logic_push_mask` marks PUSHes the compiler folds away; `variance_conflicts_static_jumps` and `members_conflict_static_jumps` reject a family whose variant PUSH feeds a static jump. |
| `crates/revmc/src/bytecode/mod.rs` | `apply_variance()` writes the classification into instruction flags; new `InstFlags::VARIANT_PUSH`; `InstData::data` gains a data-table-index meaning; `push_imm_value()` implements EVM zero-extension for immediates truncated by the physical end of code. |
| `examples/runner/src/vs_perhash_families.rs` | Registry serialization and deserialization: load a pre-built registry or scan the corpus, group, and persist. |
| `examples/runner/src/skelot_common.rs` | Shared helpers for all SkelOT binaries; re-exports the core `emse` and `skeleton` API. |

The workspace builds with `panic = "abort"`, so `catch_unwind` fallbacks are
dead code and every recoverable condition has to be checked before compilation
starts.

## Group C — Per-member table lowering in the LLVM backend

| File | What it does |
|---|---|
| `crates/revmc/src/compiler/translate.rs` | The `PUSH1..=PUSH32` arm branches on `InstFlags::VARIANT_PUSH`: load `EvmContext::imm_data_ptr`, GEP by `table_index * 32`, load an i256. Otherwise the old constant path. `CODESIZE` now loads `EvmContext::bytecode_len` at runtime instead of baking in `bytecode.code.len()`, which is what lets family members with different metadata lengths share one artifact. |
| `crates/revmc/src/compiler/mod.rs` | New entry points `translate_skeleton()` and `unsafe jit_skeleton()`, both taking a `&SkeletonVariance`; `FcxConfig` became `Clone` to carry the branch profile. |

## Group D — Dispatch and runtime context

| File | What it does |
|---|---|
| `crates/revmc-context/src/lib.rs` | `EvmContext` gains `bytecode_ptr`, `bytecode_len`, and `imm_data_ptr`; the struct-size assertion moves from 80 to 104 bytes with `offset_of` assertions at 80 / 88 / 96. New `unsafe fn call_with_interpreter_data(interpreter, host, imm_data_ptr)`; the old `call_with_interpreter` delegates with a null pointer. |
| `examples/runner/src/jit_lookup.rs` | Per-frame decision on whether to attempt JIT dispatch. |
| `examples/runner/src/aot_cache.rs` | Persistent per-hash AOT cache, compile-or-load of `.so` files. |
| `examples/runner/src/timing_handlers.rs` | Per-frame timing and perf-bracket dispatch handlers for the replay comparison. |
| `examples/runner/src/bin_common.rs` | Shared block and transaction loading, JIT compilation, and EVM handler implementations. |

The layout assertion is load-bearing. Any change to `EvmContext` field order
invalidates every compiled artifact, because the JIT emits fixed byte offsets.

## Group E — Admission guards

| Item | Status |
|---|---|
| g1: `emse.rs::tail_can_fall_through` (skeleton level) and `emse.rs::stripped_suffix_has_jumpdest` (member level) | Live. These are the two conservative guards proving execution can never reach the stripped region. A skeleton that cannot be proved safe is rejected whole. |
| g2: `emse.rs::ENFORCE_G2: bool = false` | Compiled off. g2 was replaced by interpreter alignment: the revm fork's jump-table mask closes the "jump directly into the metadata region" entrance, and shared artifacts never contained that region. |
| `crates/revmc/src/skeleton_admission.rs` (new, 348 lines) | **Dead code.** Nothing calls `check_admission`, `skeleton_fingerprint` is caller-supplied rather than derived, and PUSH counts are never compared. It is kept only because it is part of the snapshot. Do not read it as a live safety mechanism. |

The interpreter-side half of g2 lives in the revm fork, not here:
`crates/bytecode/src/legacy/emse.rs` (a byte-equivalent copy of the strip, synced
by hand) and `crates/interpreter/src/emse_jump_audit.rs` (the `[JUMP-HIT]`
counter).

## Group F — Upstream bug fixes and revm API adaptation, NOT SkelOT contributions

A reviewer diffing against `paradigmxyz/revmc` will see these changes; they are
not part of the research contribution. `revmc_fix_pr.md` writes five of them up
as a would-be upstream pull request and `REVM_API_DIFF.md` documents the revm
v34 to fork API migration.

| Change | Files | Nature |
|---|---|---|
| `resume_at` not persisted after CALL/CREATE, so a contract restarted from PC 0 | `crates/revmc-context/src/lib.rs` | Correctness fix (Bug 1 in `revmc_fix_pr.md`) |
| JIT CALL gas accounting diverged from the interpreter | `crates/revmc-builtins/src/lib.rs` | Correctness fix (Bug 2) |
| SSTORE refund rewritten to match revm's `GasParams::sstore_refund` (EIP-2200, EIP-3529) | `crates/revmc-builtins/src/gas.rs` | Correctness fix |
| DIV / SDIV / MOD / MUL moved from inline IR to builtins; SMOD zero-divisor UB | `crates/revmc-builtins/src/{ir.rs,lib.rs}`, `crates/revmc/src/compiler/translate.rs`, `crates/revmc/src/tests/smod_zero_opaque.rs` | Correctness fix |
| `Attribute::Speculatable` removed; `noalias` narrowed to parameters 1 and 2 because `Gas` and `InputsImpl` alias through `EvmContext` | `crates/revmc-builtins/src/ir.rs`, `crates/revmc/src/compiler/mod.rs` | Miscompilation fix |
| CODECOPY reads bytecode from `EvmContext` instead of two extra pointer arguments | `crates/revmc-builtins/src/{ir.rs,lib.rs}`, `translate.rs` | Segfault fix, and a prerequisite for EMSE sharing |
| i256 load and store split into four i64 lanes with explicit alignment | `crates/revmc-llvm/src/lib.rs` | Codegen correctness |
| `lld` presence probe before `-fuse-ld=lld` | `crates/revmc/src/linker.rs` | Portability fix, and an environment hazard: see the linker note below |
| revm 34 to fork API churn | `crates/revmc-cli/`, `crates/revmc-builtins/`, `tests/state-tests/` | Mechanical adaptation |
| PGO branch profiling (`profile.rs`, `set_branch_profile`, `brif_cold` weighting at JUMPI) | `crates/revmc/src/profile.rs`, `compiler/mod.rs`, `translate.rs` | Exploratory work. No paper number uses it. The three PGO binaries are not in this snapshot. |

### The linker note

`crates/revmc/src/linker.rs` probes for a bare `lld` on `PATH` before passing
`-fuse-ld=lld` to the C compiler. On the measurement machine `lld` was not on
`PATH` (only `/usr/bin/lld-21` and `/usr/bin/ld.lld-21` existed), so every
artifact behind the paper's numbers was linked with GNU `ld`. Upstream's own
installer, `.github/scripts/install_llvm_ubuntu.sh`, symlinks `lld-$v` to
`/usr/bin/lld`, which silently flips the linker in both arms and can move
compile wall clock and artifact size. The artifact `Dockerfile` and `setup.sh`
deliberately do not create that symlink.

## Group G — The measurement harness

`examples/runner/` is the harness. Eight of its binaries produce paper numbers.

| Binary | Paper result it feeds |
|---|---|
| `skelot_dataset_scan` | Table 1, Table 2, the Section 6.1 corpus figures, Figure 2, and the size bucket that Figure 6 depends on |
| `push_variance` | Section 6.2 RQ1 variant-byte shares, the tiny-versus-huge bucket contrast, Figure 4 |
| `skeleton_deployment_span` | Table 3 |
| `skelot_compile_bench` | Section 6.2 RQ2 headline, Figure 5, the Compile column of the end-to-end replay table, the Arbitrum sentence, the guard and degradation counts, and the all-variant arm behind Figure 6 |
| `skeleton_vs_perhash_bench` | The Section 6.3 correctness gate, Figure 7 and the RQ3 paired statistics, the Exec / family-frame / everything-else columns, Figure 8 and RQ4 via the per-block exclusive-time file, the Table 5 slots, and the Section 7.4 all-variant slowdown |
| `grouping_stats` | The family-build cell of the end-to-end replay table, and the family map behind Figure 6 and Figure 8 |
| `nested_family_count` | The Section 6.3 nested-frame count |
| `inspect_registry` | The Section 6.1 registry sizes and the Section 7.4 registry growth |

Ten further binaries are kept because they back a qualitative claim or were used
to validate a decision, even though no number in the paper comes from them:
`skeleton_bench` (single-block execution sanity, used by the smoke test),
`skeleton_precompile`, `skip_logic_conflicts`, `jump_hit_attribution`,
`load_reason_audit`, `hash_to_addr`, `hash_block_freq`, `snapshot_audit`,
`replay_outcomes`, and `addr_code_hash`.

## What was removed from the prototype tree when this snapshot was taken

Nothing below produced a paper number. Removals are listed so that a reviewer
comparing against the prototype repository can account for the difference.

- 29 binaries under `examples/runner/src/bin/`, and their `[[bin]]` sections in
  `examples/runner/Cargo.toml`. Two of them, `skelot_ablation_bench` and
  `frame_tx_index`, were paper-critical during submission and were superseded
  during the revision by the full-corpus ablation computed in
  `scripts/ablation_817.py`. The other 27 are pre-revision exploration of
  adaptive JIT dispatch, PGO, and instruction-cache effects. `ablation_exec.rs`,
  the support module that only `skelot_ablation_bench` used, went with them.
- `examples/compiler/` and `fuzz/`, which are upstream examples and are not
  workspace members.
- `tests/state-tests/` and the `tests/ethereum-tests` submodule. Not a workspace
  member, dead in the current workspace, and it carried hardcoded corpus paths.
- `docs/`, except the launch record `docs/plans/2026-07-30-emse-compile-realignment.md`
  and the original design and plan pair from 2026-03-09. The rest is
  pre-EMSE exploration whose numbers are stale.
- `.github/`, whose LLVM installer creates the `lld` symlink described above.
- `skeleton_registry_full.bin.pre-degradation-filter`, a 217 MB generated
  registry from the old boundary.
- Agent-session state that was already gitignored in the prototype:
  `.claude/`, `CLAUDE.md` files, `.planning/`, `.worktrees/`, and the
  `runtime_attribution/output/` and `paths.env` files.

## What was added or edited for the artifact, on top of the snapshot

- `examples/runner/src/bin/inspect_registry.rs` was **untracked** in the
  prototype repository at the snapshot commit, so no clone of `jit-integration`
  could reproduce the registry-size numbers. It is included here and given an
  explicit `[[bin]]` section rather than relying on cargo's autobins.
- `examples/runner/tests/v1_schema_compat.rs` hardcoded two corpus files, so a
  plain `cargo test` failed on any machine but the original one. It now resolves
  the corpora from `$BENCH_ROOT` and reports success without asserting when they
  are absent.
- `.cargo/config.toml` carries `net.git-fetch-with-cli = true`. On the
  measurement machine this setting lived in the user's global cargo config and
  was therefore invisible to a fresh clone, which can fail to resolve the revm
  fork.
- `rust-toolchain.toml` pins the toolchain channel. The prototype had none and
  relied on `cargo +1.91` at the call site.
- `README.md` was updated: it still documented LLVM 18 and `LLVM_SYS_180_PREFIX`.
- `upstream.diff` was generated.

## Things a reviewer will notice, stated up front

- **`crates/revmc-cranelift/` is still here.** It is the upstream legacy
  backend, untouched by SkelOT, and every paper number comes from the LLVM
  backend. It is kept because it is an optional path dependency of `revmc` that
  cargo resolves whether or not the `cranelift` feature is on, so removing it
  would mean editing the manifests of a tree we cannot rebuild here.
- **`crates/revmc/src/skeleton_admission.rs` is dead code**, as stated in Group E.
- **The compiled-in `--bench-dir` defaults still name the original author's
  paths** (`/home/ubuntu/sipeng/bench_data_*`), both in six binaries and in
  `skelot_common::chain_data_defaults`. Every script in the artifact's
  `scripts/` directory passes `--bench-dir` explicitly, so the defaults are
  never used. They were left alone rather than edited blind, because the
  snapshot was assembled without a build of the prototype.
- **`docs/plans/2026-07-30-emse-compile-realignment.md` quotes absolute paths
  from the original machine.** It is a historical record of what was run and
  when, so its paths were not rewritten. The runnable form of those commands is
  in the artifact's `scripts/`.
- **Ten `mload_overflow` tests fail under `cargo test -p revmc`**
  (`MemoryLimitOOG` versus `MemoryOOG`). They are pre-existing and unrelated to
  SkelOT: five cases instantiated across the LLVM and Cranelift backends.

## Dependency on the revm fork

All seven revm crates are pinned to
`https://github.com/SipengXie2024/skelot-revm` at rev
`db2ea6755d1d1b235843b7e9894160a0022f949b` (2026-07-30, "feat(bytecode,interpreter):
hardened jump semantics for stripped metadata"). That rev is deliberately not
the fork's tip. The fork carries the interpreter half of the EMSE story and the
build cannot resolve without it.
