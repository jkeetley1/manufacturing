#!/usr/bin/env python3
"""Run golden problems and check results against reference ranges.

Conventions (adjust to match SPEC.md):
  golden_problems/<name>.json    -> {"inputs": {...}}
  reference_ranges/<name>.json   -> {"metric": {"min": a, "max": b}, ...}

Replace `solve()` with a call into the real optimisation code.
Exits non-zero if any metric falls outside its reference range.
"""
import argparse, json, sys
from pathlib import Path


def solve(inputs: dict) -> dict:
    # TODO: call the real optimiser here and return {metric: value}.
    raise NotImplementedError("Wire tools/run_golden.py to the optimiser.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", default="golden_problems")
    ap.add_argument("--ranges", default="reference_ranges")
    a = ap.parse_args()

    problems = sorted(Path(a.problems).glob("*.json"))
    if not problems:
        print("No golden problems found - nothing to check.")
        return 0

    failures = 0
    for p in problems:
        prob = json.loads(p.read_text())
        rng_path = Path(a.ranges) / p.name
        if not rng_path.exists():
            print(f"FAIL {p.stem}: no reference range file {rng_path}")
            failures += 1
            continue
        ranges = json.loads(rng_path.read_text())
        try:
            result = solve(prob["inputs"])
        except NotImplementedError as e:
            print(f"SKIP {p.stem}: {e}")
            return 0
        for metric, bounds in ranges.items():
            v = result.get(metric)
            ok = v is not None and bounds["min"] <= v <= bounds["max"]
            print(f"{'PASS' if ok else 'FAIL'} {p.stem}.{metric} = {v} (range [{bounds['min']}, {bounds['max']}])")
            failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
