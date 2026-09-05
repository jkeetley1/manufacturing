# Controlled assumption change log

Every change to `controlled_assumptions.yaml`, `reference_ranges.yaml`, or any golden problem is recorded here **before** it takes effect. Agents draft entries; humans approve. The Data Auditor blocks any run whose dataset differs from the last approved version without a matching entry.

| # | Date | Parameter | Previous | New | Changed by | Approved by | Reason / reference |
|---|---|---|---|---|---|---|---|
| 1 | 2026-09-05 | (initial) controlled_assumptions v1 | — | v1 | Agent Engineer (draft) | *pending* | Initial scaffold; all values marked pending require human input |
| 2 | 2026-09-05 | (initial) reference_ranges v1 | — | v1 | Agent Engineer (draft) | *pending* | Deliberately wide bands; tighten per commodity |
| 3 | 2026-09-05 | (initial) golden set G01–G20 | — | 21 problems | Optimisation Scientist (draft) | *pending* | Hand solutions in each problem description |
| 4 | 2026-09-05 | golden/src/goldentest/model.py (solve) | — | HiGHS resetGlobalScheduler(True) before options | jkeetley1 (via ECP-2026-09-05-01) | *pending* | On Windows the threads option after scheduler init leaves run() unexecuted (status Not Set → 'unknown'); all 22 solver-dependent tests errored. Formulation, options and expected results unchanged. |

<!-- Example of a real entry:
| 5 | 2026-10-12 | demand.growth_rate | 3.0 % | 5.5 % | Jeff | A. Chen | Updated market study MS-2026-07 |
-->
