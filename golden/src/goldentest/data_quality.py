"""Data Auditor checks.

Design rules (from the spec):
  * Blockers gate the run. Any BLOCKER => the model must not run, regardless of score.
  * The score summarises MAJOR/MINOR findings only. It never overrides a blocker.
  * Units are checked against *declared* metadata, not guessed from magnitude.
    Magnitude heuristics are a backstop and are never a blocker on their own.
  * The Data Auditor flags. It never fixes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml

from .loader import CANONICAL_UNITS, Problem

REFERENCE_RANGES_PATH = Path(__file__).resolve().parents[3] / "reference" / "reference_ranges.yaml"


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


@dataclass
class DQFinding:
    check: str
    severity: Severity
    message: str
    location: str = ""


@dataclass
class DQReport:
    findings: List[DQFinding]
    score: float
    gate_passed: bool
    data_hash: str

    def summary(self) -> str:
        counts = {s: sum(1 for f in self.findings if f.severity == s) for s in Severity}
        verdict = "PASS" if self.gate_passed else "FAIL (blocked)"
        return (f"DQ gate: {verdict} | score {self.score:.0f}/100 | "
                + ", ".join(f"{s.value}={n}" for s, n in counts.items() if n))


def _load_reference_ranges(path: Optional[Path] = None) -> dict:
    p = path or REFERENCE_RANGES_PATH
    if p.exists():
        return yaml.safe_load(p.read_text()) or {}
    return {}


def run_checks(p: Problem, reference_ranges: Optional[dict] = None,
               today: Optional[date] = None) -> DQReport:
    ref = reference_ranges if reference_ranges is not None else _load_reference_ranges()
    today = today or date.today()
    f: List[DQFinding] = []

    # ---- 1. Declared units vs canonical (deterministic, BLOCKER) ------------
    for dim, canon in CANONICAL_UNITS.items():
        declared = p.units.get(dim)
        if declared is None:
            f.append(DQFinding("units.declared", Severity.MAJOR,
                               f"no declared unit for '{dim}' (expected '{canon}')", "units"))
        elif declared != canon:
            f.append(DQFinding("units.mismatch", Severity.BLOCKER,
                               f"declared {dim} unit '{declared}' ≠ canonical '{canon}'", "units"))

    # ---- 2. Sign / presence checks (BLOCKER) -------------------------------
    for s in p.sites:
        for name in ("production_cost", "fixed_cost", "base_capacity", "site_max_capacity",
                     "expansion_unit", "expansion_capex", "max_expansion_units"):
            v = getattr(s, name)
            if v is None:
                f.append(DQFinding("value.missing", Severity.BLOCKER,
                                   f"missing {name}", f"site:{s.id}"))
            elif v < 0:
                f.append(DQFinding("value.negative", Severity.BLOCKER,
                                   f"negative {name} = {v}", f"site:{s.id}"))
        if s.site_max_capacity is not None and s.base_capacity is not None \
                and s.base_capacity > s.site_max_capacity:
            f.append(DQFinding("capacity.base_exceeds_max", Severity.MAJOR,
                               f"base capacity {s.base_capacity} > site max {s.site_max_capacity}"
                               " — site can never open", f"site:{s.id}"))
    for c in p.customers:
        for t, d in c.demand.items():
            if d < 0:
                f.append(DQFinding("value.negative", Severity.BLOCKER,
                                   f"negative demand {d} in {t}", f"customer:{c.id}"))
    for r in p.routes:
        if r.cost is None:
            f.append(DQFinding("value.missing", Severity.BLOCKER, "missing transport cost",
                               f"route:{r.src}->{r.dst}"))
        elif r.cost < 0:
            f.append(DQFinding("value.negative", Severity.BLOCKER,
                               f"negative transport cost {r.cost}", f"route:{r.src}->{r.dst}"))
        elif r.cost == 0:
            f.append(DQFinding("loophole.zero_cost_arc", Severity.MAJOR,
                               "zero transport cost — solver will funnel flow through this arc",
                               f"route:{r.src}->{r.dst}"))

    # ---- 3. Duplicates (exact = BLOCKER, fuzzy = MAJOR) ----------------------
    _dupes(f, [s.id for s in p.sites], "site")
    _dupes(f, [c.id for c in p.customers], "customer")
    seen = set()
    for r in p.routes:
        if (r.src, r.dst) in seen:
            f.append(DQFinding("duplicate.route", Severity.BLOCKER,
                               "duplicate route definition", f"route:{r.src}->{r.dst}"))
        seen.add((r.src, r.dst))

    # ---- 4. Completeness against the spec's sets ----------------------------
    site_ids = {s.id for s in p.sites}
    routed_from = {r.src for r in p.routes}
    routed_to = {r.dst for r in p.routes}
    for s in p.sites:
        if s.id not in routed_from:
            f.append(DQFinding("completeness.site_unrouted", Severity.MINOR,
                               "site has no outbound route — can never serve demand", f"site:{s.id}"))
    for c in p.customers:
        if c.id not in routed_to and any(d > 0 for d in c.demand.values()):
            f.append(DQFinding("completeness.customer_unrouted", Severity.BLOCKER,
                               "demand node has demand but no inbound route", f"customer:{c.id}"))
        for t in p.periods:
            if t not in c.demand:
                f.append(DQFinding("completeness.demand_period", Severity.MINOR,
                                   f"no demand declared for period {t} (treated as 0)",
                                   f"customer:{c.id}"))
    for r in p.routes:
        if r.src not in site_ids:
            f.append(DQFinding("completeness.unknown_site", Severity.BLOCKER,
                               f"route references unknown site '{r.src}'", f"route:{r.src}->{r.dst}"))

    # ---- 5. Structural infeasibility warning --------------------------------
    for t in p.periods:
        dem = sum(c.demand.get(t, 0.0) for c in p.customers)
        cap = sum(min(s.site_max_capacity or 0,
                      (s.base_capacity or 0) + (s.expansion_unit or 0) * (s.max_expansion_units or 0))
                  for s in p.sites)
        if dem > cap:
            f.append(DQFinding("feasibility.demand_exceeds_capacity", Severity.MAJOR,
                               f"period {t}: demand {dem:g} t > max deliverable capacity {cap:g} t "
                               "— model will (correctly) report infeasible", f"period:{t}"))

    # ---- 6. Geography: coordinates and distance plausibility ----------------
    pos = {}
    for n in list(p.sites) + list(p.customers):
        if n.lat is None or n.lon is None:
            continue
        if not (-90 <= n.lat <= 90 and -180 <= n.lon <= 180):
            f.append(DQFinding("geo.invalid_coordinates", Severity.BLOCKER,
                               f"coordinates out of range ({n.lat}, {n.lon})", f"node:{n.id}"))
        else:
            pos[n.id] = (n.lat, n.lon)
    geo = ref.get("geography", {})
    lo, hi = geo.get("road_ratio_min", 1.0), geo.get("road_ratio_max", 2.0)
    for r in p.routes:
        if r.distance_km is None or r.src not in pos or r.dst not in pos:
            continue
        gc = _haversine_km(*pos[r.src], *pos[r.dst])
        if gc < 1e-6:
            continue
        ratio = r.distance_km / gc
        if ratio < lo - 1e-9:
            f.append(DQFinding("geo.distance_below_great_circle", Severity.BLOCKER,
                               f"stated {r.distance_km:g} km < great-circle {gc:.1f} km (ratio {ratio:.2f})",
                               f"route:{r.src}->{r.dst}"))
        elif ratio > hi:
            f.append(DQFinding("geo.distance_implausible", Severity.MAJOR,
                               f"stated {r.distance_km:g} km is {ratio:.1f}× great-circle {gc:.1f} km",
                               f"route:{r.src}->{r.dst}"))

    # ---- 7. Reference-range plausibility (backstop heuristics) -------------
    bands = ref.get("plausibility", {})
    for s in p.sites:
        _band(f, bands.get("production_cost_usd_per_t"), s.production_cost,
              "production_cost", f"site:{s.id}")
        _band(f, bands.get("expansion_capex_usd_per_unit"), s.expansion_capex,
              "expansion_capex", f"site:{s.id}", skip_zero=True)
    for r in p.routes:
        _band(f, bands.get("transport_cost_usd_per_t"), r.cost, "transport_cost",
              f"route:{r.src}->{r.dst}", skip_zero=True)

    # ---- 8. Provenance / staleness -----------------------------------------
    max_age = ref.get("provenance", {}).get("max_age_days", 365)
    for s in p.sites:
        for fld, meta in (s.provenance or {}).items():
            as_of = meta.get("as_of")
            if as_of is None:
                f.append(DQFinding("provenance.no_date", Severity.MINOR,
                                   f"{fld}: provenance has no as_of date", f"site:{s.id}"))
                continue
            d = as_of if isinstance(as_of, date) else datetime.fromisoformat(str(as_of)).date()
            age = (today - d).days
            if age > max_age:
                f.append(DQFinding("provenance.stale", Severity.MAJOR,
                                   f"{fld} is {age} days old (max {max_age}) — source: "
                                   f"{meta.get('source', 'unknown')}", f"site:{s.id}"))

    score = _score(f)
    gate = not any(x.severity == Severity.BLOCKER for x in f)
    return DQReport(findings=f, score=score, gate_passed=gate, data_hash=p.data_hash)


# --------------------------------------------------------------------------- #
def _dupes(f, ids, kind):
    seen, seen_norm = set(), {}
    for i in ids:
        if i in seen:
            f.append(DQFinding(f"duplicate.{kind}", Severity.BLOCKER,
                               f"duplicate {kind} id", f"{kind}:{i}"))
        norm = "".join(i.lower().split())
        if norm in seen_norm and seen_norm[norm] != i:
            f.append(DQFinding(f"duplicate.{kind}_fuzzy", Severity.MAJOR,
                               f"'{i}' looks like a duplicate of '{seen_norm[norm]}'", f"{kind}:{i}"))
        seen.add(i)
        seen_norm.setdefault(norm, i)


def _band(f, band, value, name, loc, skip_zero=False):
    if band is None or value is None or (skip_zero and value == 0):
        return
    lo, hi = band.get("min"), band.get("max")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        f.append(DQFinding("plausibility.out_of_band", Severity.MAJOR,
                           f"{name} = {value:g} outside reference band [{lo}, {hi}] — "
                           "possible unit or currency error", loc))


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _score(findings: List[DQFinding]) -> float:
    """100 minus weighted deductions. Blockers are NOT scored — they gate."""
    w = {Severity.MAJOR: 10, Severity.MINOR: 3, Severity.INFO: 0}
    deduction = sum(w.get(x.severity, 0) for x in findings)
    return max(0.0, 100.0 - deduction)
