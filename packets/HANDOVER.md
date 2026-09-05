# Handover — next session

## State as at 2026-09-06
On main: platform, five agent roles, golden problems G01-G20, CI, Colab demo, and the OPT-201/202
governance packets with change-log entries 1-10. Branch protection is ON and verified by
reload-and-read-back (entry 10 records the incident where it silently wasn't).

## Outstanding item 1 — land the Spec 2.1 code
Built, audited and verified at **39 passing tests**, but NOT yet on GitHub. It lives in the file
`manufacturing-update.zip` held by the repo owner. Contents:
  - `golden/src/goldentest/` — Spec 2.0 (two-echelon plant->DC->market, opening lead-times, capex
    discounted at commitment) and Spec 2.1 (delivery solutions per lane, service radius, lane
    activation cost, single-sourcing cap, integer own-fleet sizing). Model version ref-2.1.0.
  - `golden/problems/G21-G31` — eleven new hand-solved problems.
  - `demos/D03_asahi_two_echelon.yaml`, `demos/D04_asahi_distribution.yaml` — Asahi-inspired cases
    (public program facts; all volumes and unit costs illustrative estimates).
  - `demos/demo_colab.ipynb` — upgraded: runs the golden suite live, gates the data, solves D04,
    reports delivery solutions per zone and fleet per DC, cost decomposition, next-best and
    threshold re-solves, near-tie statement, eight sliders.
  - `packets/MSP-OPT-201.md`, `ECP-OPT-201.md`, `AFP-OPT-201.md`, `MSP-OPT-202.md` — the four
    packets not in the subset PR.
Land it via a PR (protection now enforces this). Then re-run the tamper test to confirm the
controls bite with no bypass available.

## Outstanding item 2 — OPT-203
See `packets/task_OPT-203.yaml`. Scope decisions are already taken there; the Optimisation
Scientist starts by writing MSP-OPT-203.

## Known findings still open (from AFP-OPT-201 / AFP-OPT-202)
- A1 MAJOR (procedural): one agent has played every role; no independent auditor exists yet.
  Fix structurally when a second account/agent is available.
- A2/A6 MINOR: no plausibility bands for handling_cost, vehicle_cost, tonnes_per_vehicle.
- A3 MINOR: infeasibility diagnosis does not name the lead time when it blocks a PRE-EXISTING
  site's expansion (it does when the site is greenfield).
- A5 MINOR: on D04 fleet vs 3PL is a near-tie, so vehicle counts swing between periods. The
  Explainer must lead with the tie rather than present the swing as a plan.
