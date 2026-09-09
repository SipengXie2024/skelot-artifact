#!/usr/bin/env python3
"""Attach on-chain addresses to the compile units that dominate execution time.

Candidate addresses come from tx.to in the local corpus; eth_getCode over Base
mainnet turns each into a code hash, which joins against the EMSE family map.
Nothing here feeds a paper number; it exists to explain what the hot families
actually are.
"""

import collections
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from keccak256 import keccak256

from paths import inp, open_text, out as out_path

CORPUS = Path(os.environ.get("BENCH_ROOT", str(Path(__file__).resolve().parent.parent / "bench_data"))) / "bench_data_base"
RPC = os.environ.get("BASE_MAINNET_RPC_URL") or os.environ.get("RPC_URL")
if not RPC:
    raise SystemExit("set BASE_MAINNET_RPC_URL (or RPC_URL) to a Base archive endpoint")
OUT = out_path("family_identity_base10k.json")

BATCH = 100


def rpc_batch(calls):
    req = urllib.request.Request(
        RPC, data=json.dumps(calls).encode(),
        headers={"Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as exc:  # noqa: BLE001 - transient RPC errors
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
            print(f"    retry {attempt + 1}: {exc}", file=sys.stderr)
    return []


def collect_addresses(blocks):
    addrs = collections.Counter()
    for b in blocks:
        p = CORPUS / "blocks_json" / f"{b}.json"
        if not p.exists():
            continue
        for tx in json.loads(p.read_text())["transactions"]:
            to = tx.get("to")
            if to:
                addrs[to.lower()] += 1
    return addrs


def main():
    fam = {}
    with open(inp("family_map_emse_base.tsv")) as f:
        for line in f:
            h, u = line.rstrip("\n").split("\t")
            fam[h] = u

    exec_us = collections.Counter()
    with open_text(inp("exclusive_per_block_base10k.tsv",
                       "exclusive_per_block_base10k.tsv.zst")) as f:
        for line in f:
            _, _, h, us = line.rstrip("\n").split("\t")
            exec_us[h] += float(us)
    total_us = sum(exec_us.values())

    start = 38004930
    sample_blocks = list(range(start, start + 400))
    addrs = collect_addresses(sample_blocks)
    print(f"candidate addresses from {len(sample_blocks)} blocks: {len(addrs):,}")

    addr_list = [a for a, _ in addrs.most_common()]
    addr_to_hash = {}
    for i in range(0, len(addr_list), BATCH):
        chunk = addr_list[i:i + BATCH]
        calls = [{"jsonrpc": "2.0", "id": j, "method": "eth_getCode",
                  "params": [a, "latest"]} for j, a in enumerate(chunk)]
        for resp in rpc_batch(calls):
            code = resp.get("result")
            if not code or code == "0x":
                continue
            addr_to_hash[chunk[resp["id"]]] = keccak256(bytes.fromhex(code[2:])).hex()
        print(f"  resolved {len(addr_to_hash):,} / {min(i + BATCH, len(addr_list)):,}")

    by_hash = collections.defaultdict(list)
    for a, h in addr_to_hash.items():
        by_hash["0x" + h].append(a)

    units = collections.Counter()
    for h, v in exec_us.items():
        units[fam.get(h, f"solo_{h}")] += v

    report = []
    for unit, us in units.most_common(25):
        members = [h for h in fam if fam[h] == unit] if unit.startswith("fam_") else \
                  [h for h in exec_us if fam.get(h, f"solo_{h}") == unit]
        ranked = sorted(((h, exec_us.get(h, 0.0)) for h in members),
                        key=lambda kv: -kv[1])
        entry = {"unit": unit, "pct_time": us / total_us * 100,
                 "members": len(members),
                 "executed": sum(1 for _, v in ranked if v > 0),
                 "top_members": []}
        for h, v in ranked[:5]:
            if v <= 0:
                break
            entry["top_members"].append(
                {"code_hash": h, "pct_time": v / total_us * 100,
                 "addresses": by_hash.get(h, [])[:5],
                 "n_addresses_seen": len(by_hash.get(h, []))})
        report.append(entry)

    OUT.write_text(json.dumps(
        {"total_exec_us": total_us, "addresses_resolved": len(addr_to_hash),
         "units": report}, indent=2))
    print(f"wrote {OUT}")

    for e in report[:12]:
        top = e["top_members"][0] if e["top_members"] else None
        addr = top["addresses"][0] if top and top["addresses"] else "unresolved"
        print(f"{e['pct_time']:6.2f}%  {e['unit'][:24]:26} "
              f"members={e['members']:>5}  hottest={addr}")


if __name__ == "__main__":
    main()
