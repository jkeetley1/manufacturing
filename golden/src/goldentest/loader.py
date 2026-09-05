"""Load golden problems from YAML.

The loader is deliberately dumb: it reads what is declared and computes a data
hash. It does NOT coerce units, fill defaults for cost fields, or "fix" anything.
Judgement about the data belongs to the Data Auditor (data_quality.py); judgement
about the model belongs to model.py.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

CANONICAL_UNITS = {"mass": "t", "currency": "USD", "energy": "MWh", "time": "period"}


@dataclass
class Site:
    id: str
    production_cost: Optional[float]
    fixed_cost: Optional[float] = 0.0
    base_capacity: Optional[float] = 0.0
    site_max_capacity: Optional[float] = None
    expansion_unit: Optional[float] = 0.0
    expansion_capex: Optional[float] = 0.0
    max_expansion_units: Optional[int] = 0
    lat: Optional[float] = None
    lon: Optional[float] = None
    provenance: Dict[str, dict] = field(default_factory=dict)  # field -> {source, as_of}


@dataclass
class Customer:
    id: str
    demand: Dict[str, float]
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class Route:
    src: str
    dst: str
    cost: Optional[float]
    distance_km: Optional[float] = None


@dataclass
class Problem:
    id: str
    name: str
    description: str
    periods: List[str]
    discount_rate: float
    units: Dict[str, str]
    sites: List[Site]
    customers: List[Customer]
    routes: List[Route]
    expected: dict
    data_hash: str = ""
    source_path: Optional[str] = None


def load_problem(path: str | Path) -> Problem:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    data_hash = hashlib.sha256(
        json.dumps({k: v for k, v in raw.items() if k != "expected"}, sort_keys=True,
                   default=str).encode()
    ).hexdigest()[:16]

    sites = []
    for s in raw.get("sites", []) or []:
        smax = s.get("site_max_capacity")
        if smax is None:
            # If undeclared, the site max is base + all expansions (no extra ceiling).
            base = s.get("base_capacity", 0.0) or 0.0
            unit = s.get("expansion_unit", 0.0) or 0.0
            mx = s.get("max_expansion_units", 0) or 0
            smax = base + unit * mx
        sites.append(Site(
            id=str(s["id"]),
            production_cost=s.get("production_cost"),
            fixed_cost=s.get("fixed_cost", 0.0),
            base_capacity=s.get("base_capacity", 0.0),
            site_max_capacity=smax,
            expansion_unit=s.get("expansion_unit", 0.0),
            expansion_capex=s.get("expansion_capex", 0.0),
            max_expansion_units=s.get("max_expansion_units", 0),
            lat=s.get("lat"), lon=s.get("lon"),
            provenance=s.get("provenance", {}) or {},
        ))

    customers = [
        Customer(id=str(c["id"]), demand={str(k): float(v) for k, v in (c.get("demand") or {}).items()},
                 lat=c.get("lat"), lon=c.get("lon"))
        for c in raw.get("customers", []) or []
    ]
    routes = [
        Route(src=str(r["from"]), dst=str(r["to"]), cost=r.get("cost"),
              distance_km=r.get("distance_km"))
        for r in raw.get("routes", []) or []
    ]

    return Problem(
        id=str(raw["id"]),
        name=raw.get("name", ""),
        description=raw.get("description", "").strip(),
        periods=[str(t) for t in raw.get("periods", ["t1"])],
        discount_rate=float(raw.get("discount_rate", 0.0)),
        units=raw.get("units", {}) or {},
        sites=sites,
        customers=customers,
        routes=routes,
        expected=raw.get("expected", {}) or {},
        data_hash=data_hash,
        source_path=str(path),
    )
