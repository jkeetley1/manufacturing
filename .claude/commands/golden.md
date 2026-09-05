---
description: Run the golden suite and summarise results
---

Run `python -m pytest golden/ -q` from the repository root. If everything
passes, report the count. If anything fails, list each failing problem with
its assertion message, and state — per 00_common_rules — that the
implementation is presumed wrong until the Optimisation Scientist rules
otherwise; do NOT edit any golden problem.
