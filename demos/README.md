# Demo cases — illustrative, NOT controlled artefacts

## ▶ Try it in your browser — no programming, nothing to install
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jkeetley1/manufacturing/blob/main/demos/demo_colab.ipynb)

Click the badge, then **Runtime → Run all** (accept the warning). Scroll down for the
network map, then move the sliders in section 4 and press ▶ on that cell to re-solve.

These are showcase datasets for demonstrating the platform end to end. Real
geography, plausible public-knowledge economics, no client data. They are not
golden problems: they carry `check: objective_only` with no asserted value and
sit outside `golden/problems/` change control on purpose.

## D01 — East-coast greenfield network
5 candidate sites (Gladstone, Townsville, Newcastle, Port Kembla, Geelong),
3 markets (Brisbane, Sydney, Melbourne), 5 periods, 10% discount rate,
greenfield build in discrete 250 kt/yr units, site cap 1,000 kt/yr.

Reference result (HiGHS, threads=1, seed 0, gap 1e-6):
  Build Gladstone (4 units immediately, 1,000 kt) + Geelong (3 units, 4th in t5).
  Never build Townsville, Newcastle or Port Kembla.
  NPV cost 4.333 bn USD. Gladstone serves Brisbane + most of Sydney;
  Geelong serves Melbourne + the Sydney remainder.
  Next-best network (no Gladstone): Townsville+Newcastle+Geelong, +76 MUSD.
  Threshold (by bisection re-solves): Gladstone drops out of the optimum if its
  production cost exceeds ~361 USD/t (base 335).

## D02 — Asahi-inspired east-coast DC network
Grounded in Asahi Beverages' public three-DC program (Deer Park VIC; Redbank
QLD, $150M, operational 2028; third Sydney DC announced 2026) and its published
manufacturing footprint. Program facts and locations are public (sources dated
in the file's provenance fields); ALL volumes and unit costs are illustrative
analyst estimates, NOT Asahi data. Single-echelon simplification: inbound
plant->DC freight folded into per-tonne site cost; two-echelon is a Spec
amendment.

Reference result (HiGHS, threads=1, seed 0, gap 1e-6):
  Build Deer Park VIC (750 kt), Redbank QLD (750 kt), Kemps Creek NSW
  (750 kt -> 1,000 kt in t3). NPV cost 1.323 bn USD.
  This reproduces the shape of Asahi's actual announced program: one DC per
  east-coast state, Melbourne-west + Ipswich + Sydney-west.
  NEAR-TIES (must be led with, per the Explainer rules): the intra-state site
  choices are ties within data accuracy - swapping Redbank for Yatala costs
  only +1.5 MUSD and Deer Park for Truganina +3.1 MUSD, far inside the error
  of the estimated costs. The three-state STRUCTURE is robust; the specific
  address within each precinct is not decided by this data. Kemps Creek vs
  Moorebank is worth +11.2 MUSD (re-solves R1-R3).
