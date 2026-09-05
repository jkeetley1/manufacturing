# Manufacturing Optimisation Platform — Agent Team Repository

Controlled repository for the agent team defined in `SPEC.md`.

## Layout
| Path | Purpose | Controlled? |
|---|---|---|
| `SPEC.md` | Team specification (paste your copy here) | yes |
| `00_common_rules.md` | Rules applied by every role at all times | yes |
| `agents/` | One system prompt per role | yes |
| `templates/` | Packet templates per role | yes |
| `assumptions/` | Controlled assumptions | **yes — Auditor sign-off** |
| `reference_ranges/` | Controlled reference ranges | **yes — Auditor sign-off** |
| `golden_problems/` | Golden problems and expected results | **yes — Auditor sign-off** |
| `reference/assumption_change_log.md` | Every change to a controlled artefact needs an entry | **yes** |
| `tools/` | CI scripts (golden-problem runner) | no |

## Running the roles in Claude Code

Open this repository in Claude Code and the five roles are available as
subagents (defined in `.claude/agents/`), each locked to its system prompt in
`agents/` and to the separation of powers: the Auditor, Data Auditor and
Explainer have no edit tools; the Engineer is forbidden from controlled paths;
the Scientist owns the reference model. Slash commands: `/audit <branch>`
(two-stage audit), `/dq <file>` (data quality report), `/golden` (run the
suite). Completed packets are filed in `packets/`.

## Rules enforced by this repo
1. `main` is protected: pull requests only, one approval, green CI.
2. Any change under `assumptions/`, `reference_ranges/` or `golden_problems/` requires Auditor approval (CODEOWNERS) and a `reference/assumption_change_log.md` entry (CI check).
3. The Auditor files an *Auditor Expectation* issue **before** reading the Engineer change packet.
4. Golden problems run on every pull request; any result outside its reference range fails the build.
