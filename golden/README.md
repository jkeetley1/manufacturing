# Golden test harness

Runnable reference implementation of the Mathematical Specification, plus 21 hand-solved golden problems and a set of Auditor-style adversarial probes.

```bash
pip install -r ../requirements.txt
python run_golden.py --record      # report + reproducibility records -> last_run.json
python -m pytest -q                # 21 golden + 7 auditor probes  (expect 28 passed)
```

## Layout
- `src/goldentest/model.py` — the formulation (Pyomo). Spec is in the module docstring.
- `src/goldentest/data_quality.py` — Data Auditor checks; blockers gate, score summarises.
- `src/goldentest/loader.py` — YAML loader; preserves nulls, computes data hash.
- `src/goldentest/runner.py` — DQ → gate → solve → compare against `expected:`.
- `problems/*.yaml` — golden problems. Each states its hand solution.
- `test_golden.py`, `test_auditor_probes.py` — pytest.

## Problem file format
```yaml
id: G05
name: ...
description: |            # hand solution written out here
units: {mass: t, currency: USD, energy: MWh, time: period}
periods: [t1]
discount_rate: 0.0
sites:      [{id, production_cost, fixed_cost, base_capacity, site_max_capacity,
              expansion_unit, expansion_capex, max_expansion_units, lat, lon, provenance}]
customers:  [{id, demand: {t1: ...}, lat, lon}]
routes:     [{from, to, cost, distance_km}]     # absent route = forbidden; absent cost = error
expected:
  status: optimal | infeasible | data_error | dq_blocked
  objective: ...            # optimal
  tolerance: 1e-6
  check: objective_only     # for tied optima
  production / open / expansion_units: {site: {period: value}}
  shipments: [{from, to, period, qty}]
  diagnosis_contains: ...   # infeasible
  error_contains: ...       # data_error
  dq: {gate: true|false, max_score: 90, findings_include: [check.names]}
```

## Adding a solver
`model.solve()` is the only place the solver is named. Add a branch that returns the same `Solution` object and the whole golden set runs against it unchanged. No solver is used for a material decision until it passes all golden problems.

## Change control
Golden problems are controlled artefacts. Changing one requires an entry in `../reference/assumption_change_log.md` and human approval.
