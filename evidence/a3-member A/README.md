# Assignment 3 Member A results

**Zipeng Chen | Branch: `feature/checkout-notification` | 7 November 2026**

Checkout confirmation is implemented in `POST /loans`. The response header
`X-Notification-Sent` reports success or failure. A failed notification keeps
the successful checkout and stock update.

| Check | Result |
|---|---|
| Before A3 | 74 passed, 13 failed; 94.69% coverage |
| New Member A tests | **11 passed** |
| Full suite on this branch | **85 passed, 13 expected failures** |
| Application line coverage | **98.47%** (321 of 326 lines) |

## Read these four files

1. **README.md** — this short explanation.
2. **pytest.txt** — actual output from the new tests and full suite.
3. **coverage-files.png** — coverage by application file.
4. **coverage-functions.png** — the functions with uncovered lines.

The function screenshot hides fully covered functions. Its 83% subtotal is only
for those displayed functions; overall application coverage is **98.47%**.

## Why 13 expected failures remain

These are existing Assignment 2 defects: missing book-field validation (3),
search ranking (2), reservation priority (2), and member loan filtering (6).
Their assertions are preserved with explicit, strict `xfail` markers, as A3
allows. They are **not fixed or counted as passed**.

The five uncovered lines are in the member API and reservation routes proposed
for Member B. Partner review, CI, and the final merged-main run are still pending.

## Run again

From `library-management` with your virtual environment active:

```powershell
python -m pytest -v tests/test_a3_Zipeng.py
python -m pytest -v --cov=app --cov-report=term-missing --cov-fail-under=90
```

The original baseline screenshots are already included in the draft report.
This folder contains local feature-branch evidence; no commits or pushes were made.
