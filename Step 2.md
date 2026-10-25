# Step 2 Existing Feature Testing

Group 81 — Library Management

Zipeng's preparation covers Steps 2a–2d. 

## Table B: Feature Coverage and Testing Responsibilities

Features are distinct user operations. The browser and JSON API versions of the same operation share one owner. Listing and filtering loans are one lookup operation; listing and filtering reservations are treated the same way. Book search is a separate catalogue operation from listing all books. Test paths below are relative to `library-management/`.

| Feature name | Related requirement ID(s) | Assigned member | Test file |
|---|---|---|---|
| Add a book | No match | Zipeng Chen | `tests/test_zipeng.py` |
| List all books | R3 (partial support for displayed details and availability) | Zipeng Chen | `tests/test_zipeng.py` |
| Search books by title or author | R1, R2, R25 | Zipeng Chen | `tests/test_zipeng.py` |
| View one book's details | R3 | Zipeng Chen | `tests/test_zipeng.py` |
| Update a book | No match | Zipeng Chen | `tests/test_zipeng.py` |
| Delete a book | No match | Zipeng Chen | `tests/test_zipeng.py` |
| Check out a book | R4, R7, R9 (queue interpretation), R16, R26 | Zipeng Chen | `tests/test_zipeng.py` |
| Return a loan | R4, R8, R15, R26 | Zipeng Chen | `tests/test_zipeng.py` |
| List and filter loans by member or book | R11, R15 | Zipeng Chen | `tests/test_zipeng.py` |
| Register a member | No match | Kate Gerrie | `tests/test_kate.py` (planned) |
| List all members | No match | Kate Gerrie | `tests/test_kate.py` (planned) |
| Look up a member by ID | R5 (internal ID interpretation) | Kate Gerrie | `tests/test_kate.py` (planned) |
| Update a member | No match | Kate Gerrie | `tests/test_kate.py` (planned) |
| Delete a member | No match | Kate Gerrie | `tests/test_kate.py` (planned) |
| Renew a loan | R10 | Kate Gerrie | `tests/test_kate.py` (planned) |
| View a loan's overdue fine | R17, R19, R20, R21 | Kate Gerrie | `tests/test_kate.py` (planned) |
| Create a reservation | R9 | Kate Gerrie | `tests/test_kate.py` (planned) |
| List and filter reservations by member or book | R9, R11 | Kate Gerrie | `tests/test_kate.py` (planned) |
| View the home page and use its navigation links | No match | Kate Gerrie | `tests/test_kate.py` (planned) |

**Requirement coverage summary:** Catalogue search and book details support R1–R3. Member lookup supports R5. Checkout, return, renewal, loan lookup, reservations, and fine calculation support parts of the borrowing, queue, account-information, and fine requirements. Add/update/delete book records, register/list/update/delete member records, and home-page navigation have no direct user-operation requirement in Table A, so they are marked “No match.” These existing operations still need tests. R27 is a broader capacity requirement, and R30 applies across the regression suite; neither is used to force a match for every record-management operation.

**Workload summary:** Zipeng has nine features and Kate has ten. Zipeng combines six book operations with checkout, return, and loan lookup. Kate combines member management with renewal, fines, reservations, and navigation. Both members have simple record operations and more complex workflows. The owner tests both API and form routes where both exist.

Related IDs indicate that an operation supports a requirement, including partial or defective support; they do not mean that the requirement passes.

## Step 2b Individual test branch

- Fetched `origin`, switched to `main`, and pulled the original main
- Created `test/zipeng` from main
- Published the initial branch and set its upstream, as required in Step 2b.
- Added all new test work on this test branch.

## Step 2c Meaningful tests

The test file uses pytest and the supplied `client` fixture from `tests/conftest.py`. The two example tests and application files are unchanged. Static inspection identifies 41 test functions and 64 parameterized cases, excluding the supplied examples.

| Zipeng's feature | Cases | Main checks |
|---|---:|---|
| Add a book | 8 | Saved fields, distinct IDs, default copies, missing required fields, zero/one-copy boundary, HTML form creation |
| List all books | 2 | Multiple complete records, unchanged state after reads, catalogue page contents |
| Search books by title or author | 7 | Partial/case-insensitive matching, all matches, exact-title/author priority, no matches, unchanged catalogue |
| View one book's details | 2 | Correct selected record and fields; nonexistent ID without state changes |
| Update a book | 3 | Full/partial updates, preserved omitted fields, subsequent GET/search, unknown ID |
| Delete a book | 4 | Removal from lookup/list/search, unrelated records preserved, unknown/repeated deletion, HTML form deletion |
| Check out a book | 18 | Member/book/date fields, inventory decrement, last-copy boundary, exhausted stock, unknown IDs, overdue eligibility, due-today boundary, returned overdue loans, queue priority; API and form paths |
| Return a loan | 8 | Return date, one-copy restoration, other active loan preserved, repeated/unknown returns, atomicity after book deletion; API and form paths |
| List and filter loans | 12 | All records and dates, member/book filters, combined filters, no matches, HTML display |
| **Total** | **64** | **All nine assigned features** |

**Test design:** Assertions check returned fields and subsequent GET requests, not just status codes. Workflows combine creation, checkout, return, update, deletion, and lookup. Book and member IDs deliberately differ in filter tests so that comparing the wrong ID field cannot accidentally pass.

**Controlled dates:** The `assessment_day` fixture freezes only the application's imported date objects at 21 October 2026. An overdue loan's due date is set directly in isolated test data because the public API cannot change it. The computer's clock and the running development server are not changed. State assertions refer to the reference application's in-memory lifetime, not storage across restarts.

**Error assertions:** For invalid API checkouts, the tests accept any 4xx rejection rather than inventing a required 400/403/409 code. For HTML forms, rejection is assessed through unchanged loans and inventory because the UI may redirect. Missing-field tests require a client-validation response based on the creation schema. Where necessary, exception propagation is disabled for that test so that a server error can be checked as an HTTP response. These are test configuration changes only.


## Defect checks to explain after execution

The following expectations come from Table A or the documented input schema. Step 1 and source inspection indicate possible failures, but **no Step 2 test results have been collected**. These tests remain ordinary assertions; none is skipped, marked xfail, or changed to accept a defect.
