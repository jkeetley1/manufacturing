"""Reference manufacturing network design model (MILP).

This is the *mathematical specification* rendered in Pyomo. It is owned by the
Optimisation Scientist role. The Agent Engineer's production implementation is
audited against this model on the golden problems, never the other way round.

Formulation (single commodity, multi-period)
--------------------------------------------
Sets
    I   candidate sites
    J   demand nodes (customers)
    T   planning periods (ordered)
    A   ⊆ I×J   permitted transport arcs

Parameters (canonical units: tonnes, USD, per period)
    FixedCost[i]          USD / period while site i is open
    ProdCost[i]           USD / t
    BaseCap[i]            t / period available when site i is open
    SiteMax[i]            t / period hard ceiling permitted at site i
    Unit[i]               t / period added per discrete expansion unit
    ExpCapex[i]           USD per expansion unit, charged in the period installed
    MaxUnits[i]           maximum expansion units ever installable at i
    Demand[j,t]           t / period
    TransCost[i,j]        USD / t on arc (i,j)
    DF[t]                 discount factor = 1 / (1 + r)^(k) for k-th period

Variables
    Open[i,t]        ∈ {0,1}   site i is open in period t
    Prod[i,t]        ≥ 0       production at i in t
    Ship[i,j,t]      ≥ 0       flow on arc (i,j) in t
    Exp[i,t]         ∈ ℤ≥0     cumulative expansion units installed at i by t
    NewExp[i,t]      ≥ 0       units installed in t  (= Exp[i,t] − Exp[i,t−1])

Constraints
    (Demand)      Σ_i Ship[i,j,t] = Demand[j,t]                    ∀ j,t
    (Balance)     Prod[i,t] = Σ_j Ship[i,j,t]                      ∀ i,t
    (Capacity)    Prod[i,t] ≤ BaseCap[i]·Open[i,t] + Unit[i]·Exp[i,t]
    (SiteMax)     BaseCap[i]·Open[i,t] + Unit[i]·Exp[i,t] ≤ SiteMax[i]·Open[i,t]
    (ExpOpen)     Exp[i,t] ≤ MaxUnits[i]·Open[i,t]
    (Monotone)    Exp[i,t] ≥ Exp[i,t−1],   Open[i,t] ≥ Open[i,t−1]
    (NewExp)      NewExp[i,t] = Exp[i,t] − Exp[i,t−1]   (Exp[i,t0−1] := 0)

Objective
    min Σ_t DF[t] · ( Σ_i FixedCost[i]·Open[i,t] + ProdCost[i]·Prod[i,t]
                      + ExpCapex[i]·NewExp[i,t] + Σ_(i,j)∈A TransCost[i,j]·Ship[i,j,t] )

Deliberate modelling choices (Scientist decisions, not Engineer decisions)
    * Capacity is linear in Open and Exp — no bilinear Open·Exp term. The
      (ExpOpen) constraint makes Exp = 0 whenever Open = 0, which is what makes
      the linearisation exact.
    * Expansion is discrete (integer units). Continuous expansion is a
      different model and must not be silently substituted.
    * Decommissioning is out of scope, hence the (Monotone) constraints.
    * An arc absent from A is *forbidden*, not free. A zero-cost arc is a
      data-quality finding, not a modelling feature.
"""
from __future__ import annotations

import hashlib
import inspect
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Tuple

import pyomo.environ as pyo

from .loader import Problem

MODEL_VERSION = "ref-1.0.0"


class ModelDataError(ValueError):
    """Raised when input data violates the model's preconditions."""


class InfeasibleError(RuntimeError):
    """Raised when the solver proves the problem infeasible.

    Carries a human-readable diagnosis so that "no feasible solution" is never
    the whole answer.
    """

    def __init__(self, diagnosis: str):
        super().__init__(diagnosis)
        self.diagnosis = diagnosis


@dataclass
class Solution:
    status: str
    objective: float
    production: Dict[str, Dict[str, float]]
    shipments: Dict[Tuple[str, str, str], float]
    open: Dict[str, Dict[str, int]]
    expansion_units: Dict[str, Dict[str, int]]
    reproducibility: Dict[str, object] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Model construction
# --------------------------------------------------------------------------- #
def build_model(p: Problem) -> pyo.ConcreteModel:
    _validate(p)
    m = pyo.ConcreteModel(name=f"{p.id}:{p.name}")

    m.I = pyo.Set(initialize=[s.id for s in p.sites])
    m.J = pyo.Set(initialize=[c.id for c in p.customers])
    m.T = pyo.Set(initialize=list(p.periods), ordered=True)
    m.A = pyo.Set(within=m.I * m.J, initialize=[(r.src, r.dst) for r in p.routes])

    sites = {s.id: s for s in p.sites}
    m.FixedCost = pyo.Param(m.I, initialize={i: sites[i].fixed_cost for i in m.I})
    m.ProdCost = pyo.Param(m.I, initialize={i: sites[i].production_cost for i in m.I})
    m.BaseCap = pyo.Param(m.I, initialize={i: sites[i].base_capacity for i in m.I})
    m.SiteMax = pyo.Param(m.I, initialize={i: sites[i].site_max_capacity for i in m.I})
    m.Unit = pyo.Param(m.I, initialize={i: sites[i].expansion_unit for i in m.I})
    m.ExpCapex = pyo.Param(m.I, initialize={i: sites[i].expansion_capex for i in m.I})
    m.MaxUnits = pyo.Param(m.I, initialize={i: sites[i].max_expansion_units for i in m.I})
    m.Demand = pyo.Param(
        m.J, m.T,
        initialize={(c.id, t): c.demand.get(t, 0.0) for c in p.customers for t in p.periods},
    )
    m.TransCost = pyo.Param(m.A, initialize={(r.src, r.dst): r.cost for r in p.routes})
    m.DF = pyo.Param(
        m.T, initialize={t: 1.0 / (1.0 + p.discount_rate) ** k for k, t in enumerate(p.periods)}
    )

    m.Open = pyo.Var(m.I, m.T, within=pyo.Binary)
    m.Prod = pyo.Var(m.I, m.T, within=pyo.NonNegativeReals)
    m.Ship = pyo.Var(m.A, m.T, within=pyo.NonNegativeReals)
    m.Exp = pyo.Var(m.I, m.T, within=pyo.NonNegativeIntegers)
    m.NewExp = pyo.Var(m.I, m.T, within=pyo.NonNegativeReals)

    def prev(t):
        idx = m.T.ord(t)
        return None if idx == 1 else m.T.at(idx - 1)

    def _demand(m, j, t):
        inbound = [i for i in m.I if (i, j) in m.A]
        if not inbound:
            # No arc can ever serve this node. If it has demand the problem is
            # infeasible by construction — say so now rather than let Pyomo
            # choke on a constant constraint.
            if pyo.value(m.Demand[j, t]) > 0:
                raise InfeasibleError(_diagnose_infeasibility(p))
            return pyo.Constraint.Skip
        return sum(m.Ship[i, j, t] for i in inbound) == m.Demand[j, t]

    m.DemandBalance = pyo.Constraint(m.J, m.T, rule=_demand)
    m.MaterialBalance = pyo.Constraint(
        m.I, m.T,
        rule=lambda m, i, t: m.Prod[i, t] == sum(m.Ship[i, j, t] for j in m.J if (i, j) in m.A),
    )
    m.Capacity = pyo.Constraint(
        m.I, m.T,
        rule=lambda m, i, t: m.Prod[i, t] <= m.BaseCap[i] * m.Open[i, t] + m.Unit[i] * m.Exp[i, t],
    )
    m.SiteMaximum = pyo.Constraint(
        m.I, m.T,
        rule=lambda m, i, t: m.BaseCap[i] * m.Open[i, t] + m.Unit[i] * m.Exp[i, t]
        <= m.SiteMax[i] * m.Open[i, t],
    )
    m.ExpansionRequiresOpen = pyo.Constraint(
        m.I, m.T, rule=lambda m, i, t: m.Exp[i, t] <= m.MaxUnits[i] * m.Open[i, t]
    )

    def _monotone_exp(m, i, t):
        pt = prev(t)
        return pyo.Constraint.Skip if pt is None else m.Exp[i, t] >= m.Exp[i, pt]

    def _monotone_open(m, i, t):
        pt = prev(t)
        return pyo.Constraint.Skip if pt is None else m.Open[i, t] >= m.Open[i, pt]

    def _new_exp(m, i, t):
        pt = prev(t)
        prior = 0 if pt is None else m.Exp[i, pt]
        return m.NewExp[i, t] == m.Exp[i, t] - prior

    m.MonotoneExpansion = pyo.Constraint(m.I, m.T, rule=_monotone_exp)
    m.MonotoneOpen = pyo.Constraint(m.I, m.T, rule=_monotone_open)
    m.NewExpansion = pyo.Constraint(m.I, m.T, rule=_new_exp)

    m.TotalCost = pyo.Objective(
        expr=sum(
            m.DF[t]
            * (
                sum(
                    m.FixedCost[i] * m.Open[i, t]
                    + m.ProdCost[i] * m.Prod[i, t]
                    + m.ExpCapex[i] * m.NewExp[i, t]
                    for i in m.I
                )
                + sum(m.TransCost[a] * m.Ship[a, t] for a in m.A)
            )
            for t in m.T
        ),
        sense=pyo.minimize,
    )
    return m


def _validate(p: Problem) -> None:
    """Preconditions the model refuses to run without. Fail loudly, not quietly."""
    errors = []
    if not p.sites:
        errors.append("no candidate sites")
    if not p.customers:
        errors.append("no demand nodes")
    if not p.periods:
        errors.append("no planning periods")
    seen = set()
    for s in p.sites:
        if s.id in seen:
            errors.append(f"duplicate site id '{s.id}'")
        seen.add(s.id)
        for fname in ("fixed_cost", "production_cost", "base_capacity", "site_max_capacity",
                      "expansion_unit", "expansion_capex", "max_expansion_units"):
            v = getattr(s, fname)
            if v is None:
                errors.append(f"site '{s.id}': missing {fname}")
            elif v < 0:
                errors.append(f"site '{s.id}': negative {fname} ({v})")
    seen = set()
    for c in p.customers:
        if c.id in seen:
            errors.append(f"duplicate customer id '{c.id}'")
        seen.add(c.id)
        for t, d in c.demand.items():
            if d < 0:
                errors.append(f"customer '{c.id}': negative demand in {t} ({d})")
            if t not in p.periods:
                errors.append(f"customer '{c.id}': demand for unknown period '{t}'")
    site_ids = {s.id for s in p.sites}
    cust_ids = {c.id for c in p.customers}
    for r in p.routes:
        if r.src not in site_ids:
            errors.append(f"route from unknown site '{r.src}'")
        if r.dst not in cust_ids:
            errors.append(f"route to unknown customer '{r.dst}'")
        if r.cost is None:
            errors.append(f"route {r.src}->{r.dst}: missing transport cost")
        elif r.cost < 0:
            errors.append(f"route {r.src}->{r.dst}: negative transport cost ({r.cost})")
    if p.discount_rate is None or p.discount_rate < 0:
        errors.append(f"invalid discount rate ({p.discount_rate})")
    if errors:
        raise ModelDataError("; ".join(errors))


# --------------------------------------------------------------------------- #
# Solve
# --------------------------------------------------------------------------- #
def solve(p: Problem, solver_name: str = "highs", mip_gap: float = 1e-6,
          time_limit: float = 60.0, threads: int = 1) -> Solution:
    """Solve with HiGHS via Pyomo's APPSI interface.

    Only HiGHS is wired in here. Adding another solver (Gurobi, CBC, a
    quantum-inspired heuristic) means adding a branch that returns the same
    Solution object — the golden problems then run unchanged against it.
    """
    from pyomo.contrib.appsi.base import TerminationCondition as TC
    from pyomo.contrib.appsi.solvers import Highs

    if solver_name != "highs":
        raise RuntimeError(f"solver '{solver_name}' is not wired into the reference harness")

    m = build_model(p)
    opt = Highs()
    if not opt.available():
        raise RuntimeError("HiGHS (highspy) is not available")

    # HiGHS initialises a process-wide thread scheduler on first use; on some
    # platforms (observed: Windows, highspy 1.9-1.15) setting 'threads' after
    # that leaves run() unexecuted and model status 'Not Set' -> pyomo 'unknown'.
    # Reset the scheduler so the deterministic threads=1 setting takes effect.
    # Change-log: reference/assumption_change_log.md entry 4 (ECP-2026-09-05-01).
    import highspy
    highspy.Highs().resetGlobalScheduler(True)

    # Deterministic settings: single thread, fixed seed, explicit gap.
    opt.config.load_solution = False
    opt.config.time_limit = time_limit
    opt.config.mip_gap = mip_gap
    opt.highs_options["threads"] = threads
    opt.highs_options["random_seed"] = 0

    t0 = time.perf_counter()
    res = opt.solve(m)
    runtime = time.perf_counter() - t0

    tc = res.termination_condition
    if tc in (TC.infeasible, TC.infeasibleOrUnbounded):
        raise InfeasibleError(_diagnose_infeasibility(p))
    if tc == TC.unbounded:
        raise RuntimeError("problem is unbounded — objective has no lower bound; check for "
                           "negative cost coefficients or a missing demand constraint")
    if tc != TC.optimal:
        raise RuntimeError(f"solver terminated with '{tc.name}' (gap/time limit reached?)")

    res.solution_loader.load_vars()
    obj = pyo.value(m.TotalCost)

    sol = Solution(
        status="optimal",
        objective=obj,
        production={i: {t: _r(pyo.value(m.Prod[i, t])) for t in m.T} for i in m.I},
        shipments={(i, j, t): _r(pyo.value(m.Ship[i, j, t])) for (i, j) in m.A for t in m.T},
        open={i: {t: int(round(pyo.value(m.Open[i, t]))) for t in m.T} for i in m.I},
        expansion_units={i: {t: int(round(pyo.value(m.Exp[i, t]))) for t in m.T} for i in m.I},
    )
    sol.reproducibility = _reproducibility_record(p, res, solver_name, mip_gap, threads,
                                                  runtime, obj)
    return sol


def _r(x: float, nd: int = 6) -> float:
    return 0.0 if abs(x) < 10 ** -nd else round(x, nd)


def _diagnose_infeasibility(p: Problem) -> str:
    """Cheap structural diagnosis. Not an IIS, but always says *something* useful."""
    reasons = []
    served = {c.id: set() for c in p.customers}
    for r in p.routes:
        served.setdefault(r.dst, set()).add(r.src)
    for c in p.customers:
        if not served.get(c.id) and any(d > 0 for d in c.demand.values()):
            reasons.append(f"customer '{c.id}' has demand but no inbound route")
    for t in p.periods:
        total_demand = sum(c.demand.get(t, 0.0) for c in p.customers)
        total_cap = sum(min(s.site_max_capacity,
                            s.base_capacity + s.expansion_unit * s.max_expansion_units)
                        for s in p.sites)
        if total_demand > total_cap + 1e-9:
            reasons.append(
                f"period '{t}': total demand {total_demand:g} t exceeds maximum deliverable "
                f"capacity {total_cap:g} t across all sites"
            )
    for s in p.sites:
        if s.base_capacity > s.site_max_capacity:
            reasons.append(f"site '{s.id}': base capacity {s.base_capacity:g} exceeds site "
                           f"maximum {s.site_max_capacity:g} — site can never open")
    if not reasons:
        reasons.append("structural checks passed; infeasibility arises from interaction of "
                       "constraints — request an IIS from the solver")
    return "infeasible: " + "; ".join(reasons)


def _reproducibility_record(p: Problem, res, solver_name, mip_gap, threads, runtime, obj):
    src = inspect.getsource(build_model)
    return {
        "model_version": MODEL_VERSION,
        "model_hash": hashlib.sha256(src.encode()).hexdigest()[:16],
        "data_version": p.data_hash,
        "problem_id": p.id,
        "solver": solver_name,
        "solver_version": _highs_version(),
        "configuration": {"mip_rel_gap": mip_gap, "threads": threads, "random_seed": 0},
        "optimisation_gap": _gap(res.best_feasible_objective, res.best_objective_bound),
        "objective": obj,
        "runtime_s": round(runtime, 4),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_assumptions": {"discount_rate": p.discount_rate, "units": p.units},
    }


def _gap(best, bound):
    if best is None or bound is None or best == 0:
        return None
    return abs(best - bound) / abs(best)


def _highs_version() -> str:
    try:
        import highspy
        h = highspy.Highs()
        return f"HiGHS {h.version()}"
    except Exception:  # pragma: no cover
        return "HiGHS (version unknown)"
