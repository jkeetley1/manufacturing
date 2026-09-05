# Setup — do these once

1. Replace placeholders: `SPEC.md`, `00_common_rules.md`, every file in `agents/`, and add the packet templates to `templates/`.
2. Edit `.github/CODEOWNERS`: swap `@AUDITOR-HANDLE`, `@SCIENTIST-HANDLE`, `@REPO-OWNER-HANDLE` for real GitHub usernames.
3. Push from inside this folder:

       git init
       git add .
       git commit -m "Initial structure from SPEC"
       git branch -M main
       git remote add origin https://github.com/jkeetley1/manufacturing.git
       git push -u origin main

4. GitHub -> Settings -> Branches -> Add rule for `main`:
   - Require a pull request before merging; Require approvals = 1
   - Dismiss stale approvals on new commits
   - Require review from Code Owners  (Team/Enterprise plan on private repos)
   - Require status checks: `golden-problems`, `changelog-required` (they appear after the first workflow run)
   - Do not allow bypassing the above settings
5. Wire `tools/run_golden.py::solve()` to the real optimiser and add golden problems + reference ranges via a PR.
6. Dry run: change a file in `assumptions/` on a branch without touching `CHANGELOG.md` -> the PR must be blocked.
