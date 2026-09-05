---
description: Run the Data Auditor over a problem or dataset file
---

Run the data-auditor subagent over `$ARGUMENTS` (a path under
`golden/problems/` or a dataset file). It must produce a complete Data Quality
Report per `templates/data_quality_report.md`, including gate verdict, score,
findings with severity and location, and the reference-ranges version used.
