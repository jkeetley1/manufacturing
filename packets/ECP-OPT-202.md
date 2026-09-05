# Change Packet

| Field | Value |
|---|---|
| Task | OPT-202 |
| Spec version implemented | 2.1 (MSP-OPT-202, GATE 1 approved 2026-09-06 by jkeetley1) |
| Author | Agent Engineer |
| Change id | ECP-OPT-202 (stacked on ECP-OPT-201) |
| Material | **yes** — objective, capacity, golden set |

## 1. Requirement (Spec §5–6)
`(Service) Ship2[k,z,c,t]=0 if Dist>Radius[c]`; `(LaneUse) Ship2 ≤ min(LaneCap, Demand[z,t])·Use`;
`(MaxChannels) Σ Use ≤ MaxChannels[z]`; `(Fleet) Σ_{fleet lanes} Ship2/TPV ≤ Vehicles[k,t]`;
`(FleetOpen) Vehicles ≤ MaxVehicles·Open`; objective + `Σ DF(ActFixed·Use + VehicleCost·Vehicles)`.

## 2. Assumptions
Lanes keyed (DC, zone, channel); `Use` binaries created only where ActFixed>0, LaneCap finite or
MaxChannels finite. `MaxVehicles` default = ⌊Σ_z Demand / min TPV⌋+1 — an exact bound, not a big-M.

## 3. Replaces
Spec 2.0 `A² ⊆ K×J`: one lane per DC→market, no fleet.

## 4. Files changed
`loader.py`, `model.py`, `runner.py`, `data_quality.py`, `__init__.py`; golden G27–G31;
change-log rows 8–9; `demos/D04_asahi_distribution.yaml`, `demos/demo_colab.ipynb`, `demos/README.md`.

## 6. Schema
Route: `channel`, `lane_capacity`, `fixed_cost`, `tonnes_per_vehicle`. DC: `vehicle_cost`,
`max_vehicles`. Customer: `max_channels`. Top-level `channels: {name: {uses_fleet, service_radius_km}}`.

## 7. Deviation requests — none.

## 9. Test results
| Stage | Result |
|---|---|
| Baseline (OPT-201) | 34 passed |
| After model change, before new goldens | **34 passed** (regression exact) |
| After G27–G31 | **39 passed** |
| Mutation: `Vehicles` continuous | G27, G28 **fail**; restored → pass |
| DQ defect found by the gate on D04 | duplicate-lane check keyed (src,dst) blocked legitimate multi-channel lanes → fixed to (src,dst,channel) |

## 10. Regression — routes without `channel` → `default`; G01–G26 objectives unchanged.

## 11. Solver impact — MILP; D04 (255 lanes, 12 zones, 5 periods) solves in ~1.5 s.

## 12. Known limitations
Fleet vs 3PL near-equal on D04 estimates → vehicle counts flip between periods (a real near-tie).
No vehicle re-positioning, no fleet lead time, no multi-drop routing. No plausibility bands yet for
handling_cost, vehicle_cost or TPV.

## 15. Human decisions
GATE 3 audit (AFP-OPT-202); GATE 4 merge; acceptability of D04 defaults for the public demo.
