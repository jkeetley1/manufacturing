# Severity scale

| Severity | Meaning | Audit consequence | Data-quality consequence |
|---|---|---|---|
| **BLOCKER** | Result cannot be trusted / run must not proceed | Automatic REJECT | Gate FAIL — run does not start |
| **MAJOR** | Likely wrong under realistic conditions, or a loophole exists | REJECT unless human accepts risk in writing | Run proceeds; finding attached to Reproducibility Record; score −10 |
| **MINOR** | Quality/robustness issue; result unlikely to change | PASS WITH FINDINGS | Score −3 |
| **INFO** | Observation | Logged | Logged |

Rules
- Blockers are never averaged away by a score.
- Unit or currency mismatch on any cost or capacity field → BLOCKER.
- Golden problem failure → BLOCKER.
- Stage-1 / stage-2 divergence in an audit → at least MAJOR until resolved.
- Any change to a controlled assumption without a change-log entry → BLOCKER.
