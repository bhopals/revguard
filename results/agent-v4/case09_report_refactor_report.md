# Code review: Deduplicate budget queries in reports

> Pure refactor: extracts the repeated budget-row query into a _budgets_for_month helper and tidies naming. No behavior change intended.

**Verdict: approve.** No blocking defects found. Every hypothesis raised during review was either confirmed fixed in the diff or rejected under verification.