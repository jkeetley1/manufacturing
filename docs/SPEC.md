# Manufacturing Optimisation Platform — Agent Team Specification
*Roles, separation of powers, artefacts and controls — 5 September 2026*

# 1. Purpose

This document specifies how a team of AI agents builds, verifies and explains a manufacturing network optimisation platform — software that answers questions such as *where should we build, how large should each plant be, and how should the network operate?*

The governing principle is **separation of powers**. No agent approves its own work. Modelling decisions, implementation decisions, verification and explanation are held by different agents with different objectives, so that a single mistaken assumption cannot travel unchallenged from requirement to board paper.

A second principle follows from the first: **every agent's objective is stated, and the objectives conflict on purpose.** The Engineer optimises for delivery. The Auditor optimises for finding failure. The Scientist optimises for mathematical fidelity. The Data Auditor optimises for refusing bad inputs. The Explainer optimises for grounded, verifiable narrative. Two cooperative agents tend to agree with each other; this design makes agreement something that has to be earned.

# 2. The five roles

| Role | Owns | Optimises for | May not |
|---|---|---|---|
| Optimisation Scientist | The mathematical model | Fidelity to manufacturing economics; tractability | Write production code |
| Agent Engineer | The software implementation | Delivery of the smallest coherent change | Change the mathematics; approve own work |
| Agent Auditor | Verification of changes | Discovering circumstances in which the implementation is wrong | Modify the implementation |
| Data Auditor | Fitness of input data | Refusing data that would produce precisely wrong answers | Fix data; be switched off by a client |
| Decision Explainer | Narrative of results | Grounded explanation and sensitivity | Optimise; assert anything not traceable to solver output |

Structurally: **Scientist → Engineer → Auditor** form the change pipeline. The **Data Auditor sits underneath** every run. The **Decision Explainer sits above** every approved result.

## 2.1 Optimisation Scientist

**Role.** Own the mathematical model independently of its software implementation.

**Mission.** Translate manufacturing economics into optimisation mathematics that is correct, tractable and honest about its approximations.

**Story.** As the Optimisation Scientist, I receive a domain requirement. I decide how it should be represented mathematically — sets, parameters, variables, constraints, objective — and I decide what problem class that keeps us in. I state the alternatives I rejected and why. I write small hand-solvable test problems with known answers so that the Auditor has an independent oracle. I approve or reject deviation requests from the Engineer. When the Auditor finds a commercially absurd result, I determine whether the fault is in the model or in the code. I never write production code.

**Why the role exists.** Consider the requirement *a factory becomes progressively more capital-efficient as its capacity increases*. Under a minimisation objective, an economies-of-scale capex curve is concave, which makes the problem non-convex. Representing it as piecewise-linear with binaries, as discrete plant-size options, as a smooth nonlinear curve, or as a single scale coefficient are five different models with different solvers, different accuracy and different data requirements. That choice belongs to someone whose objective is mathematical fidelity, not delivery.

**Decision criteria the Scientist must state** for any representation choice:

- data actually available (a capex curve, or three vendor quotes?)
- problem class it keeps us in (LP, MILP, MINLP)
- accuracy needed at the decision boundary
- solve-time budget at production scale (sites × periods × products)
- how the approximation fails outside its validity range

**Output.** A *Mathematical Specification Packet* (§5.2), versioned, plus one or more golden test problems (§6).

**Rules.**

- The Scientist does not build a prototype that becomes the implementation. Any toy model written to prove tractability is disposable and is not shown to the Engineer.
- Big-M values, tolerances, scaling and linearisation choices are modelling decisions and live in the spec, not in code comments.

## 2.2 Agent Engineer

**Role.** Build the platform from mathematical specification through to working, tested software.

**Mission.** Convert an approved specification into reliable software, data models and solver formulations.

**Story.** As the Agent Engineer, I receive an approved task with its mathematical specification. I inspect the existing architecture, data model, formulation and tests before changing anything. I design the smallest coherent implementation that satisfies the specification, implement it, add or update tests, run the validation suite and the golden problems, document my assumptions, and submit a change packet for independent audit. I must not mark my own work as production-ready.

**Optimiser-specific duty.** If a change touches a capacity constraint, an objective coefficient, plant-opening logic or a transport relationship, I explain the mathematical change, not merely the code change. For the requirement *plants may only be expanded in discrete 100 ktpa increments*, the packet states:

```
Capacity[i,t] = BaseCapacity[i] + 100 × ExpansionUnits[i,t]
ExpansionUnits[i,t] ∈ ℤ,  0 ≤ ExpansionUnits[i,t] ≤ MaxExpansionUnits[i]
ExpansionUnits[i,t] ≥ ExpansionUnits[i,t−1]
```

*where ExpansionUnits is a non-negative integer variable bounded by site-specific expansion limits, i indexes candidate sites and t indexes planning periods. The third line prevents capacity from shrinking between periods.*

That is substantially safer than "updated capacity.py".

**Deviation rule.** When the specification cannot be implemented as written — the solver lacks SOS2 support, a big-M needs tightening, a scaling problem appears — the Engineer raises a *deviation request* to the Scientist. The Engineer never resolves it unilaterally. The Auditor receives the amended specification, not the original.

**Output.** A *Change Packet* (§5.3).

## 2.3 Agent Auditor

**Role.** Independently assess whether the Engineer's implementation is mathematically, technically and commercially correct.

**Mission.** Find reasons the proposed change should not be trusted.

**Story.** As the Agent Auditor, I receive the requirement, the mathematical specification and the code — and, in a *second stage only*, the Engineer's change packet. I derive the expected behaviour myself before I read the Engineer's account of it. I inspect the implementation, run adversarial and boundary tests, compare outputs against golden problems and independently calculated answers, identify unsupported assumptions and classify findings by severity. I cannot modify the implementation I am auditing.

**System instruction, in effect:** *Your objective is not to confirm that the Engineer is correct. Your objective is to discover circumstances under which the implementation is incorrect.*

**The five questions.**

1. **Did we build what was requested?** Not *does the code run* but *does the behaviour correspond to the business requirement*, via the specification. A faithful implementation of a wrong specification is still wrong — question 2 covers the specification as well as the code.
2. **Is the mathematics correct?** Objective function; sign conventions; units; integer/binary definitions; bounds; demand balance; material balance; capacity; logistics; investment timing; discounting; taxes and currency; infeasibility handling.
3. **Can the model exploit a loophole?** Optimisers are exceptionally good at exploiting modelling mistakes. Concrete probes: list every arc and variable with zero or missing cost; report which bounds are binding at the optimum; perturb each cost class by ±10 % and flag implausible network flips; inspect shadow prices on the LP relaxation for absurd values; flag any single route or site carrying more than a stated share of total flow.
4. **Does it fail correctly?** Impossible demand, missing coordinates, negative prices, zero capacity, no feasible sites, extreme demand, duplicate facilities, mismatched units, missing energy price — and also *unbounded* problems. A trustworthy platform says *no feasible solution, and here is why*. Infeasibility without a diagnosis is half an answer.
5. **Can we reproduce the answer?** Every material result retains the *Reproducibility Record* (§5.7). A board decision must be recreatable months later.

**Adversarial repertoire.** Extreme values; missing data; contradictory constraints; unit mistakes; rounding; solver infeasibility; degeneracy; multiple equivalent optima; unrealistic economic arbitrage; temporal leakage; GIS anomalies.

**Near-ties.** Multiple equivalent optima deserve particular attention in site selection. If two sites are within the optimality gap of each other, the solver has picked one by rounding noise and management will see a decision that is not one. The Auditor must surface near-ties explicitly; the Explainer must present them as ties.

**Output.** An *Audit Findings Packet* (§5.4) with a pass/reject verdict.

## 2.4 Data Auditor

**Role.** Assess whether input data is fit to be optimised.

**Mission.** Stop bad data before it reaches the model. *A perfect optimisation model operating on bad data gives you a very precisely wrong answer.*

**Story.** As the Data Auditor, I run before every optimisation — not only when code changes, because data changes without code changing. I check declared units against canonical units, signs, completeness against the specification's sets, duplicates, geography, plausibility against shared reference ranges, and provenance age. I produce a Data Quality Report with a gate verdict and a score. I flag; I never fix. Corrections go to a data owner.

**Design rules.**

- **Blockers gate; the score summarises.** Any BLOCKER stops the run regardless of score. A dataset scoring 94/100 with one capex table in AUD instead of USD does not run.
- **Units are checked against declared metadata, not guessed.** Tonnes versus kilograms, wet versus dry, USD versus AUD, $/MWh versus $/kWh cannot be told from a number. Every parameter carries declared unit, currency, basis and as-of date. Magnitude heuristics are a backstop and never a blocker alone.
- **Completeness is defined by the specification's sets.** "Missing plant" only means something against the Scientist's set definitions: every site has every required parameter; every demand node has at least one inbound arc; every period has a price.
- **Geography is cheap and powerful.** Stated road distance divided by great-circle distance should sit in roughly 1.0–2.0×. Below 1.0 is physically impossible (BLOCKER). Coordinates must lie in the declared region.
- **Staleness needs provenance.** Every cost assumption carries source and as-of date; older than the configured maximum age is MAJOR.
- **Diffs, not just snapshots.** Report what changed between this dataset version and the last version that produced an approved result.

**Shared artefact.** The plausibility bands used here are the same bands the Agent Auditor uses to judge *commercially absurd*. One file: `reference/reference_ranges.yaml`.

**Output.** A *Data Quality Report* (§5.5), attached to the Reproducibility Record.

## 2.5 Decision Explainer

**Role.** Explain why the optimiser made the decision it made.

**Mission.** Convert an optimisation result into management insight without inventing anything.

**Story.** As the Decision Explainer, I receive an approved result and its Reproducibility Record. I decompose the objective by cost class and by site. I run parametric re-solves to find the thresholds at which the decision changes. I write an explanation in which every number traces to a solver output, a cost decomposition or a re-solve. I state near-ties as ties. I do not optimise and I do not approve.

**Target output.**

> *Gladstone was selected instead of Townsville despite $23m higher capex because electricity was $14/MWh cheaper and average inbound freight was $7.30/t lower. Over the 20-year model this improves NPV by $116m. If Gladstone power exceeds $108/MWh, Townsville becomes the preferred site.*

**Grounding rules.**

- Thresholds such as *$108/MWh* cannot be read off a MILP solution — duals are unreliable in the presence of integers. They come from parametric re-solves, and the re-solve budget is part of the run configuration.
- Every quantitative claim carries a reference to its source artefact (decomposition table row, re-solve id).
- Explanations are themselves auditable. The Agent Auditor spot-checks explanation claims against the artefacts. An LLM narrating a result will produce fluent, plausible text; fluency is not evidence.
- If the decision is a near-tie, the explanation leads with that fact.

**Output.** An *Explanation Report* (§5.6).

# 3. Workflow

## 3.1 The gated pipeline

```
Human / Product requirement
  → Optimisation Scientist: mathematical specification + golden problems
  → Human approval of specification                       [GATE 1]
  → Agent Engineer: implementation + change packet
  → Automated tests + golden problems                     [GATE 2]
  → Agent Auditor stage 1: independent expectation (spec + code)
  → Agent Auditor stage 2: change packet released; findings; verdict
  → Auditor pass / reject                                 [GATE 3]
  → Human approval for material changes                   [GATE 4]
  → Merge / release
  → Data Auditor (every run)                              [RUN GATE]
  → Solve → Reproducibility Record
  → Decision Explainer → Explanation Report
```

## 3.2 Two-stage disclosure to the Auditor

The Auditor's independence is the point of the Auditor. If it reads the Engineer's assumptions first, two agents converge on the same mistake.

- **Stage 1:** the Auditor receives the requirement, the mathematical specification, the code and the data. It writes down, and files, its own expected behaviour, including expected results on the golden problems.
- **Stage 2:** the change packet is released. The Auditor compares its expectation to the Engineer's account. Divergences are findings in their own right, whichever party turns out to be correct.

Both documents are retained so that divergence is visible.

## 3.3 Loop and escalation

- **Reject** returns the change to the Engineer with the findings packet. The Engineer addresses findings and resubmits. The Auditor re-audits *from stage 1* for any finding classified MAJOR or above.
- A change may loop at most **three** times. A fourth rejection escalates to a human with both parties' full packets.
- The Auditor's verdict is binding on the Engineer. It is advisory to the human at GATE 4 — a human may override with a logged reason.

## 3.4 Materiality

A change is **material**, and therefore requires human approval at GATE 4 regardless of audit findings, if it touches any of:

- the objective function or any of its coefficients
- capacity, site-maximum or expansion logic
- plant-opening or investment-timing logic
- discounting, tax, currency or escalation
- any controlled assumption (§7)
- any golden problem (§6)

Materiality is determined by the *specification diff*, not by the Engineer's self-assessment.

# 4. Severity scale and outcomes

| Severity | Meaning | Consequence |
|---|---|---|
| **BLOCKER** | Result cannot be trusted or run must not proceed | Audit: automatic reject. DQ: run does not start. |
| **MAJOR** | Result is likely wrong under realistic conditions, or a loophole exists | Audit: reject unless human accepts risk in writing. DQ: run proceeds, finding attached to Reproducibility Record, score −10. |
| **MINOR** | Quality or robustness issue, result unlikely to change | Audit: pass with findings logged. DQ: score −3. |
| **INFO** | Observation | Logged. |

Rules:

- Any BLOCKER anywhere yields a reject or a blocked run. Scores do not average away blockers.
- Unit or currency mismatches on cost or capacity fields are always BLOCKER.
- A divergence between the Auditor's stage-1 expectation and the Engineer's stated behaviour is at least MAJOR until resolved.

# 5. Artefacts and packet formats

Templates for each artefact are in `templates/`. Summaries follow.

## 5.1 Task record (`templates/task.yaml`)

```
TASK              OPT-143
BUSINESS REQ      Allow candidate sites to have a maximum permitted plant capacity.
SOURCE            Approved product requirement.
EXPECTED BEHAVIOUR Plant capacity must never exceed the site maximum.
MATH REQUIREMENT  Capacity[i,t] <= SiteMaxCapacity[i] * Open[i,t]     (authored by Scientist, spec v1.4)
ACCEPTANCE TEST   Site max 500 ktpa; demand 900 ktpa; single candidate site.
                  Expected: model reports INFEASIBLE with a diagnosis naming the
                  capacity shortfall. It must not produce 900 ktpa from the site.
MATERIAL          yes (capacity logic)
```

The MATHEMATICAL REQUIREMENT line is authored by the Scientist and carries the specification version. It is not part of the incoming requirement.

## 5.2 Mathematical Specification Packet (Scientist)

Sets · parameters with units · variables with domains · constraints · objective · linearisation and big-M choices · validity range of every approximation · alternatives rejected and why · expected problem class and solve-time at production scale · golden problems supplied · open questions for humans.

## 5.3 Change Packet (Engineer)

Requirement and spec version · assumptions · what the change *replaces* (prior formulation or logic) · files/modules changed · mathematical formulation affected, stated in mathematics · schema changes · deviation requests raised and their resolution · tests added · test and golden-problem results · regression check (old inputs, feature off → old solution reproduced) · solver-class impact (LP→MILP, expected solve-time change) · known limitations · expected optimisation behaviour · sample input and output · areas requiring human decision.

## 5.4 Audit Findings Packet (Auditor)

Stage-1 independent expectation (filed before packet release) · divergences from Engineer account · findings by the five questions, each with severity, evidence and reproduction steps · adversarial probes run and results · golden problem results · near-ties detected · verdict (PASS / PASS WITH FINDINGS / REJECT) · materiality flag.

## 5.5 Data Quality Report (Data Auditor)

Dataset version and hash · gate verdict · score · findings by check with severity and location · diff from last approved dataset · provenance summary (oldest assumption, count past max age) · reference-ranges version used.

## 5.6 Explanation Report (Explainer)

Decision statement · cost decomposition table (by class, by site) · comparison to next-best alternative · sensitivity thresholds with re-solve ids · near-tie statement · list of every quantitative claim with its source artefact · limitations of the explanation.

## 5.7 Reproducibility Record

Attached to every material result:

```
model_version        data_version (hash)      solver / solver_version
configuration        random_seed              threads / hardware
optimisation_gap     objective                full solution file
runtime              timestamp                input assumptions (controlled set version)
data_quality_report  spec_version             explanation_report (when produced)
```

Thread count and hardware are recorded because MILP solutions can differ across thread counts even with a fixed seed.

# 6. Golden test problems

Maintain 20–100 tiny optimisation problems whose answers are known by hand. The reference harness in `golden/` ships with 21, covering:

| Category | Problems |
|---|---|
| Cost selection, capacity, opening economics | G01, G02, G03a, G03b |
| Discrete expansion, expand-vs-open, multi-period timing | G05, G06, G10 |
| Transport assignment, discounting | G07, G11 |
| Tied optima (objective-only check) | G08 |
| Fail-correctly: infeasible with diagnosis | G04, G09, G16 |
| Fail-correctly: refuse bad data | G13, G15, G18 |
| Data Auditor gate: units, geography | G14, G17 |
| Data Auditor warnings that do not block | G19, G20 |
| Degenerate: zero demand | G12 |

Rules:

- Every problem states its hand solution in its description.
- Problems with tied optima assert the objective value only, never the solution.
- Include known-infeasible and known-unbounded cases. Infeasible cases assert on the diagnosis text.
- The golden set is under the same change control as controlled assumptions (§7). An agent quietly changing a golden test to make it pass is the single most important failure to prevent.
- Every solver the platform ever adopts — HiGHS, Gurobi, CBC, quantum-inspired heuristics, eventually quantum hardware — must pass the full golden set before it is used for a material decision.

# 7. Controlled assumptions and change control

The following are model assumptions, not software parameters: discount rate · tax · commodity and product prices · demand forecasts · capex assumptions · energy costs · plant life · minimum utilisation · carbon cost · hurdle rate · cost escalation · exchange rates · reference plausibility ranges · golden problems.

They live in versioned assumption sets (`reference/controlled_assumptions.yaml`). Every run records which set version it used. Every change is logged in `reference/assumption_change_log.md`:

```
Parameter      Demand growth
Previous       3.0 %
New            5.5 %
Changed by     <name>
Date           5 Sep 2026
Reason         Updated market study (ref MS-2026-07)
Approved by    <name>
```

Agents may *propose* changes to controlled assumptions. No agent may approve one.

# 8. Reference harness

`golden/` contains a runnable reference implementation of the current mathematical specification in Pyomo, solved with HiGHS:

- `src/goldentest/model.py` — the formulation, with the specification in its docstring
- `src/goldentest/data_quality.py` — Data Auditor checks
- `src/goldentest/loader.py` — YAML loader with declared units and data hashing
- `src/goldentest/runner.py` — evaluates each problem against its declared expectation
- `problems/*.yaml` — the golden problems
- `test_golden.py`, `test_auditor_probes.py` — pytest entry points
- `run_golden.py --record` — CLI report with reproducibility records

The reference model is owned by the Scientist. The production platform is audited against it; it is never the other way round.

# 9. Deploying as a client-facing cloud service

The roles and gates above are unchanged whether the platform is internal or sold as a service. What changes is *who owns which artefact*. An internal tool can hard-code one company's reality; a service cannot.

## 9.1 Ownership of artefacts

| Artefact | Platform (shared) | Per client (tenant) |
|---|---|---|
| Reference model, golden set G01–G20, agent prompts | ✔ | |
| Platform-layer plausibility bands (unit/currency 1000× tells) | ✔ | |
| Controlled assumption set | starter set only, labelled illustrative | ✔ authoritative |
| Commodity plausibility bands | | ✔ applied on top of platform layer |
| Client golden problems (e.g. a known past decision) | | ✔ |
| Reproducibility Records, DQ reports, Explanation Reports | | ✔ |
| Approvers for GATE 1 and GATE 4 | | ✔ named roles |

Rules: a client layer may tighten a platform band, never loosen it. The platform refuses to issue a *material* result until the tenant has approved its own assumption set — otherwise the vendor's defaults quietly become the client's board paper.

## 9.2 Resolved design decisions (recommended defaults)

1. **Decommissioning** — in scope, per-tenant toggle, off by default. Brownfield studies need it; greenfield studies do not. Golden problems ship for both branches.
2. **Controlled assumptions** — no global values. Each tenant holds a versioned set; the platform ships a documented starter set (10 % discount rate, 20-year plant life, wide bands) marked illustrative.
3. **Plausibility bands** — two layers as in §9.1. The Data Auditor applies both.
4. **Auditor verdicts** — BLOCKER verdicts are binding on humans too, subject to a *logged override*: the override, its author and reason are written into the Reproducibility Record and appear in the Explanation Report. A result nobody can silently force through is a feature.
5. **Data Auditor gate** — clients may configure MAJOR/MINOR thresholds and their own bands; they may not disable blockers.
6. **Maximum assumption age** — 365 days platform default, per-tenant configurable downward only.

## 9.3 Product consequences

- **The decision dossier is the deliverable.** Package Reproducibility Record + DQ report + Explanation Report + assumption-set snapshot as one exportable artefact. That is what survives an investment committee.
- **Client golden problems gate solver upgrades.** Every solver change must pass the platform set *and* each tenant's own problems before it touches that tenant's runs.
- **Solver tiering is a performance tier, never a correctness tier.** HiGHS default; commercial solvers as a paid tier; identical golden gate for both.
- **Human gates become role-based approvals.** The platform enforces that an approver is not the submitter.
- **Tenant isolation is a modelling concern.** Assumption sets, ranges, golden problems and records are isolated per tenant; only the reference model and platform-layer bands are shared.

## 9.4 Remaining decisions requiring human input

1. Retention period for Reproducibility Records and full solution files (regulatory and contractual).
2. Re-solve budget for the Decision Explainer per tenant tier.
3. Whether client golden problems are visible to the vendor for support, or sealed.
4. Approval workflow tooling (in-product vs existing client change-management systems).
