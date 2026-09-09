# SkelOT Runtime Frontend Attribution Notes

Created: 2026-05-13 UTC

This note records the methodology, conclusion, and measured data for the
SkelOT (`S_auto`) versus Naive AOT runtime attribution experiment.

## Bottom line

The current evidence supports a top-level additive TMA-L1 decomposition, but
not a strict lower-level pie chart inside `frontend_bound`.

TMA-L1 shows that the SkelOT slot reduction is almost entirely
`frontend_bound`. Lower-level PMU evidence then points to instruction-fetch
latency / L1 instruction-cache footprint as the mechanism. The lower-level
counters are diagnostic evidence, not mutually exclusive accounting buckets.

## Why TMA L2/L3 was not directly usable

The host is an Intel Sapphire Rapids PMU as seen by Linux:

```text
perf version: 6.17.13
kernel: 6.17.0-1013-aws
CPU: Intel Xeon Platinum 8488C
PMU name: sapphire_rapids
virtualization: KVM
```

Direct TMA L2/L3 metric attempts failed:

```text
perf stat -M tma_L2_group sleep 0.1
perf stat -M tma_L3_group sleep 0.1
perf stat --topdown --td-level 2 sleep 0.1
perf stat --topdown --td-level 3 sleep 0.1
```

Failure mode:

```text
Unable to find PMU or event on a PMU of 'topdown-retiring'
Unable to find event on a PMU of 'topdown-fetch-lat'
```

`/sys/bus/event_source/devices/cpu/caps/pmu_name` reports
`sapphire_rapids`, but the kernel sysfs event aliases do not expose
`topdown-retiring`, `topdown-fetch-lat`, or `topdown-fe-bound`. Setting
`kernel.perf_event_paranoid=-1` enables PMU access, but it does not create
missing kernel PMU aliases. A raw `r20a4` probe was also tested as a possible
fetch-latency slot event and returned zero on the real benchmark, so it was
rejected.

## Methodology

### Additive TMA-L1 accounting

The benchmark event set `tma_l1` records:

```text
cycles
instructions
topdown_slots
uops_retired_slots
topdown_bad_spec_slots
topdown_backend_bound_slots
```

Frontend-bound slots are inferred by subtraction:

```text
frontend_bound =
  topdown_slots
  - uops_retired_slots
  - topdown_bad_spec_slots
  - topdown_backend_bound_slots
```

This top-level partition is additive:

```text
slots = retiring + bad_spec + backend_bound + frontend_bound
```

### Lower-level frontend evidence

Because direct TMA L2/L3 metrics are not usable on this host, two raw-event
proxy groups were run under the same per-target JIT-call envelope.

`tma_l2_bw` checks frontend bandwidth / DSB-MITE delivery:

```text
idq.dsb_cycles_any
idq.dsb_cycles_ok
idq.mite_cycles_any
idq.mite_cycles_ok
```

Derived proxy:

```text
DSB limited cycles  = idq.dsb_cycles_any  - idq.dsb_cycles_ok
MITE limited cycles = idq.mite_cycles_any - idq.mite_cycles_ok
```

`tma_l3_fetch` checks instruction-fetch latency / code footprint:

```text
icache_data.stalls
icache_tag.stalls
offcore_requests_outstanding.cycles_with_demand_code_rd
l2_rqsts.code_rd_miss
```

These are not additive children of `frontend_bound`; they are evidence for the
mechanism.

## Data

### TMA-L1 additive slot accounting

Source: `examples/runner/scripts/runtime_attribution/output/perf_p1_summary.json`

Six runs (`r1` to `r6`):

```text
delta_topdown_slots                         -8136.458 slots/call
delta_frontend_bound_slots                  -8149.718 slots/call
delta_backend_bound_slots                    +165.010 slots/call
delta_bad_spec_slots                         -141.415 slots/call
delta_retiring_slots                          -10.335 slots/call
additive_residual_slots                         1.8e-12
```

Interpretation: the net slot reduction is localized to frontend-bound slots.
Backend-bound slots increase slightly, so backend is an offset rather than a
saving slice.

### TMA L2 frontend-bandwidth proxy

Source:
`examples/runner/scripts/runtime_attribution/output/tma_l23_probe/perf_p1_summary.json`

Three runs (`r1` to `r3`):

```text
delta_cyc                                  -1134.240 cycles/call
delta_idq_dsb_limited_cycles                 -3.921 cycles/call
delta_idq_mite_limited_cycles                -0.729 cycles/call
delta_idq_limited_cycles_total               -4.650 cycles/call
```

Interpretation: DSB/MITE bandwidth does not explain the frontend-bound saving.
The proxy movement is tiny relative to the roughly 1K+ cycle/call runtime delta
and the roughly 8K slot/call frontend-bound delta.

### TMA L3/L4 instruction-fetch proxy

Source:
`examples/runner/scripts/runtime_attribution/output/tma_l23_probe/perf_p1_summary.json`

Three runs (`r1` to `r3`):

```text
delta_cyc                                  -1231.037 cycles/call
delta_icache_data_stalls                   -1029.971 cycles/call
delta_icache_tag_stalls                     -252.545 cycles/call
delta_l2_rqsts_code_rd_miss                  -19.165 misses/call
delta_offcore_cycles_demand_code_rd            0.000 cycles/call
```

Interpretation: the frontend-bound saving is best explained as instruction
fetch latency / L1 instruction-cache footprint. It is not a decoder/uop-cache
bandwidth story, and it is not an offcore/DRAM code-fetch story on this
workload.

## Figure guidance

Do not use a strict pie chart for lower-level frontend evidence.

Use:

```text
Top panel: additive TMA-L1 slot deltas
  Frontend bound, Backend bound, Bad speculation, Retiring

Bottom panel: lower-level evidence bars
  I-cache data stalls, I-cache tag stalls, L2 code-read misses,
  DSB/MITE bandwidth proxy
```

Reviewer-safe wording:

```text
The additive TMA-L1 decomposition localizes the runtime saving to
frontend-bound slots. Lower-level PMU evidence identifies the mechanism as
instruction-fetch latency / L1I footprint: L1I data/tag stalls and L2 code-read
misses fall sharply, while DSB/MITE bandwidth proxies move by only a few
cycles per call and offcore code-read cycles are zero.
```

