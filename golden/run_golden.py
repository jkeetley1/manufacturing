#!/usr/bin/env python
"""Run every golden problem and print a report. Exit code 1 if any fail."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from goldentest.runner import evaluate_all  # noqa: E402


def main():
    outcomes = evaluate_all()
    width = max(len(o.problem_id) for o in outcomes)
    for o in outcomes:
        mark = "PASS" if o.passed else "FAIL"
        dq = o.dq.summary() if o.dq else ""
        print(f"[{mark}] {o.problem_id:<{width}}  {o.status:<11} {o.message[:70]}")
        print(f"       {dq}")
        for f in o.failures:
            print(f"       ! {f}")
    n_fail = sum(not o.passed for o in outcomes)
    print(f"\n{len(outcomes) - n_fail}/{len(outcomes)} golden problems passed")
    if "--record" in sys.argv:
        out = Path("last_run.json")
        out.write_text(json.dumps(
            [{"id": o.problem_id, "passed": o.passed, "status": o.status,
              "dq": o.dq.summary() if o.dq else None,
              "reproducibility": o.solution.reproducibility if o.solution else None}
             for o in outcomes], indent=2, default=str))
        print(f"reproducibility records written to {out}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
