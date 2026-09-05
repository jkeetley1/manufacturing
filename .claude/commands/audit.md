---
description: Run a full two-stage audit of a change branch (Agent Auditor)
---

Audit the change on branch `$ARGUMENTS` using the agent-auditor subagent.

Enforce the two-stage rule in this order and do not deviate:
1. Stage 1 — give the subagent ONLY: the task record, `docs/SPEC.md`,
   `git diff main...$ARGUMENTS`, `golden/problems/`, and the data. Tell it to
   file its independent expectation in full, with expected golden results.
2. Only after the expectation is written: release the Engineer's Change Packet
   from `packets/` (or the PR description) and have it complete stages 2–5 of
   `templates/audit_findings.md`, run the suite, and issue a verdict.

Output the completed Audit Findings Packet verbatim.
