"""Evaluate golden problems against their declared expected results.

Workflow per problem (mirrors the platform's run-time gate):
    load -> Data Auditor checks -> [gate] -> build/validate -> solve -> compare

A problem passes only if every declared expectation holds. Expectations that
are not declared are not checked — a golden problem asserts exactly what the
Optimisation Scientist hand-solved, nothing more.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .data_quality import DQReport, run_checks
from .loader import Problem, load_problem
from .model import InfeasibleError, ModelDataError, Solution, solve

PROBLEMS_DIR = Path(__file__).resolve().parents[2] / "problems"


@dataclass
class Outcome:
    problem_id: str
    passed: bool
    status: str                     # optimal | infeasible | data_error | dq_blocked | error
    failures: List[str] = field(default_factory=list)
    dq: Optional[DQReport] = None
    solution: Optional[Solution] = None
    message: str = ""


def evaluate(path: str | Path) -> Outcome:
    p = load_problem(path)
    exp = p.expected
    want = exp.get("status", "optimal")
    fails: List[str] = []

    dq = run_checks(p)
    _check_dq(exp.get("dq"), dq, fails)

    if want == "dq_blocked":
        if dq.gate_passed:
            fails.append("expected the Data Auditor to block, but the gate passed")
        return Outcome(p.id, not fails, "dq_blocked", fails, dq)

    # The platform would stop here when the gate fails. In the golden harness we
    # continue *deliberately*, because we also want to prove the model fails
    # correctly when bad data does get through (defence in depth).
    try:
        sol = solve(p)
        got = "optimal"
    except ModelDataError as e:
        return _finish(p, "data_error", want, fails, dq, msg=str(e),
                       extra=lambda: _contains(str(e), exp.get("error_contains"), "error", fails))
    except InfeasibleError as e:
        return _finish(p, "infeasible", want, fails, dq, msg=e.diagnosis,
                       extra=lambda: _contains(e.diagnosis, exp.get("diagnosis_contains"),
                                               "diagnosis", fails))
    except Exception as e:  # noqa: BLE001
        fails.append(f"unexpected error: {type(e).__name__}: {e}")
        return Outcome(p.id, False, "error", fails, dq, message=str(e))

    if want != "optimal":
        fails.append(f"expected status '{want}' but solver returned an optimal solution")
        return Outcome(p.id, False, got, fails, dq, sol)

    _compare_solution(exp, sol, fails)
    return Outcome(p.id, not fails, "optimal", fails, dq, sol,
                   message=f"objective {sol.objective:,.4f}")


def evaluate_all(problems_dir: Path = PROBLEMS_DIR) -> List[Outcome]:
    return [evaluate(f) for f in sorted(problems_dir.glob("*.yaml"))]


# --------------------------------------------------------------------------- #
def _finish(p, got, want, fails, dq, msg, extra):
    if want != got:
        fails.append(f"expected status '{want}', got '{got}': {msg}")
    else:
        extra()
    return Outcome(p.id, not fails, got, fails, dq, message=msg)


def _contains(text, needle, label, fails):
    if needle and needle not in text:
        fails.append(f"{label} should contain '{needle}'; got: {text}")


def _check_dq(spec, dq: DQReport, fails):
    if not spec:
        return
    if "gate" in spec and dq.gate_passed != bool(spec["gate"]):
        fails.append(f"DQ gate expected {'PASS' if spec['gate'] else 'FAIL'}, got {dq.summary()}")
    if "max_score" in spec and dq.score > spec["max_score"]:
        fails.append(f"DQ score {dq.score} > expected max {spec['max_score']}")
    if "min_score" in spec and dq.score < spec["min_score"]:
        fails.append(f"DQ score {dq.score} < expected min {spec['min_score']}")
    present = {f.check for f in dq.findings}
    for name in spec.get("findings_include", []):
        if name not in present:
            fails.append(f"DQ finding '{name}' expected but not raised (got {sorted(present)})")


def _compare_solution(exp, sol: Solution, fails):
    tol = float(exp.get("tolerance", 1e-6))
    if "objective" in exp:
        want = float(exp["objective"])
        if abs(sol.objective - want) > tol * max(1.0, abs(want)):
            fails.append(f"objective {sol.objective:.6f} ≠ expected {want:.6f} (tol {tol})")
    if exp.get("check") == "objective_only":
        return
    for key in ("production", "open", "expansion_units"):
        for site, per_t in (exp.get(key) or {}).items():
            for t, want in per_t.items():
                got = getattr(sol, key).get(site, {}).get(t)
                if got is None:
                    fails.append(f"{key}[{site},{t}] missing from solution")
                elif abs(got - want) > tol * max(1.0, abs(want)):
                    fails.append(f"{key}[{site},{t}] = {got} ≠ expected {want}")
    for s in exp.get("shipments") or []:
        k = (s["from"], s["to"], s["period"])
        got = sol.shipments.get(k)
        if got is None:
            fails.append(f"shipment {k} missing from solution")
        elif abs(got - s["qty"]) > tol * max(1.0, abs(s["qty"])):
            fails.append(f"shipment {k} = {got} ≠ expected {s['qty']}")
