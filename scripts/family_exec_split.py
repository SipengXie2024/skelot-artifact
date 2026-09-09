#!/usr/bin/env python3
"""Split each replay arm's execution time into family frames and everything else.

The end-to-end replay table reports three columns per arm: total execution
wall clock, the part spent inside frames whose contract belongs to a shared
family, and the remainder. The driver reports the first and the per-target
totals; this join produces the other two.

Family = sum of mode_reports[0].per_target[].total_us, in seconds
Other  = exec_wall_seconds - Family

Reads the three exec_replay_*.json files, preferring anything you produced in
results/ over the copies shipped in data/.
"""

import json

from paths import inp

ARMS = [
    ("Interpreter", "exec_replay_interpreter_base.json"),
    ("Naive AOT", "exec_replay_per_hash_base.json"),
    ("SkelOT", "exec_replay_skeleton_base.json"),
]


def split(rel):
    report = json.loads(inp(rel).read_text())["mode_reports"][0]
    wall = report["exec_wall_seconds"]
    family = sum(t["total_us"] for t in report["per_target"]) / 1e6
    return wall, family, wall - family


def main():
    print(f"{'arm':>12} {'exec (s)':>10} {'family (s)':>11} {'other (s)':>10} "
          f"{'targets':>8}")
    print("-" * 55)
    for name, rel in ARMS:
        report = json.loads(inp(rel).read_text())["mode_reports"][0]
        wall, family, other = split(rel)
        print(f"{name:>12} {wall:>10.1f} {family:>11.1f} {other:>10.1f} "
              f"{len(report['per_target']):>8,}")
    print()
    print("The paper reports the family and other columns for the two AOT arms")
    print("only. The interpreter row is shown here because the driver measures")
    print("the same per-target window in every arm.")


if __name__ == "__main__":
    main()
