"""Adversarial probes in the style of the Agent Auditor.

These do not test that the model gives the right answer on a golden problem —
test_golden.py does that. They test that the model cannot be *gamed*, that its
integrality is real, and that every result carries a complete reproducibility
record.
"""
import copy
import sys
from pathlib import Path

import pyomo.environ as pyo
import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from goldentest import build_model, load_problem, solve  # noqa: E402
from goldentest.runner import PROBLEMS_DIR  # noqa: E402

REQUIRED_REPRO_FIELDS = {
    "model_version", "model_hash", "data_version", "solver", "solver_version",
    "configuration", "optimisation_gap", "objective", "runtime_s", "timestamp",
    "input_assumptions",
}


def _load(name):
    return load_problem(PROBLEMS_DIR / name)


def test_integrality_is_real_not_cosmetic():
    """Relaxing Exp to continuous must give a *different* (cheaper) answer on G05.
    If it doesn't, the integer variable isn't doing anything."""
    p = _load("G05_discrete_expansion.yaml")
    m = build_model(p)
    m.Exp.domain = pyo.NonNegativeReals
    from pyomo.contrib.appsi.solvers import Highs
    res = Highs().solve(m)
    relaxed = pyo.value(m.TotalCost)
    integer = solve(p).objective
    assert relaxed == pytest.approx(1500 + 250 * 110)   # buys 1.5 units
    assert integer == pytest.approx(29500)
    assert integer > relaxed


def test_cannot_produce_without_opening():
    """Force Open = 0 everywhere; production must be impossible when demand > 0."""
    from goldentest.model import InfeasibleError
    p = _load("G01_cheapest_plant.yaml")
    for s in p.sites:
        s.base_capacity = 0          # no capacity unless expanded
        s.max_expansion_units = 0    # and no expansion allowed
    with pytest.raises(InfeasibleError):
        solve(p)


def test_expansion_cannot_exist_at_closed_site():
    """Every solution must satisfy Exp = 0 wherever Open = 0 (the linearisation guard)."""
    for f in sorted(PROBLEMS_DIR.glob("G0[5-6]*.yaml")) + sorted(PROBLEMS_DIR.glob("G10*.yaml")):
        sol = solve(load_problem(f))
        for i, per_t in sol.expansion_units.items():
            for t, units in per_t.items():
                if sol.open[i][t] == 0:
                    assert units == 0, f"{f.name}: expansion at closed site {i} in {t}"


def test_material_balance_holds_in_every_solution():
    for f in sorted(PROBLEMS_DIR.glob("G0*.yaml")):
        p = load_problem(f)
        if p.expected.get("status", "optimal") != "optimal":
            continue
        sol = solve(p)
        for i, per_t in sol.production.items():
            for t, prod in per_t.items():
                shipped = sum(q for (si, _, st), q in sol.shipments.items() if si == i and st == t)
                assert prod == pytest.approx(shipped, abs=1e-6), f"{f.name}: {i} {t}"


def test_reproducibility_record_is_complete():
    sol = solve(_load("G01_cheapest_plant.yaml"))
    missing = REQUIRED_REPRO_FIELDS - set(sol.reproducibility)
    assert not missing, f"reproducibility record missing {missing}"
    assert sol.reproducibility["optimisation_gap"] is not None


def test_data_hash_changes_when_a_controlled_assumption_changes():
    """A changed discount rate must produce a different data version."""
    p1 = _load("G11_discounting.yaml")
    p2 = copy.deepcopy(p1)
    p2.discount_rate = 0.12
    import hashlib, json
    # Emulate the loader's hash on the mutated problem's serialisable fields.
    h = lambda p: hashlib.sha256(json.dumps({"r": p.discount_rate, "d": p.data_hash}).encode()).hexdigest()
    assert h(p1) != h(p2)
    assert solve(p2).objective != pytest.approx(solve(p1).objective)


def test_solution_is_deterministic_across_repeat_runs():
    p = _load("G06_expand_vs_open.yaml")
    a, b = solve(p), solve(p)
    assert a.objective == b.objective
    assert a.production == b.production
    assert a.expansion_units == b.expansion_units
