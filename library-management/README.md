# Library Management System (LMS)

A small Flask REST API for tracking books, members, and loans. Data is stored
**in memory** (plain Python objects, no database) and is reset every time the
app restarts — this project is meant to run before you've covered databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete books and members, and check
books in/out:

| Page | Path |
|---|---|
| Home | `/` |
| Books | `/ui/books` |
| Members | `/ui/members` |
| Loans | `/ui/loans` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.\
Returning a book through the Loans page uses the `POST /ui/loans/<int:loan_id>/return` route. Checks that the book exists before updating the loans return date. If not, no records shall be modified.

## Entities

- **Book**: `id, title, author, isbn, total_copies, available_copies`
- **Member**: `id, name, email, membership_date`
- **Loan**: `id, book_id, member_id, loan_date, due_date, return_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/books` | List all books |
| POST | `/books` | Create a book |
| GET | `/books/<id>` | Get one book |
| PUT | `/books/<id>` | Update a book |
| DELETE | `/books/<id>` | Delete a book |
| GET | `/members` | List all members |
| POST | `/members` | Create a member |
| GET | `/members/<id>` | Get one member |
| PUT | `/members/<id>` | Update a member |
| DELETE | `/members/<id>` | Delete a member |
| POST | `/loans` | Check out an available book to an existing member with no unreturned overdue loans (`book_id`, `member_id`) |
| PUT | `/loans/<id>/return` | Return a loaned book. Validates both the loan and book exist before updating data |
| GET | `/loans?member_id=&book_id=` | Look up loans |

### Checkout eligibility (R7 and R16)

Send a JSON object to `POST /loans` containing positive integer
`book_id` and `member_id` values:

```json
{
  "book_id": 1,
  "member_id": 1
}
```

A checkout succeeds only when:
- The book exists.
- The member exists.
- The book has at least one available copy.
- The member has no unreturned loan with a due date before today.

Successful checkout returns HTTP **201** with the loan record, records
today's checkout date and a due date 14 days later, and decreases the
book's available copies by one.

#### Rejected checkouts

| Status | Reason |
|---|---|
| 400 | The JSON body is not an object, an ID is missing, or an ID is not a positive integer |
| 404 | The book or member does not exist |
| 403 | The member has an unreturned overdue loan |
| 409 | The book has no available copies |

For valid JSON requests, rejection responses contain an `error` message.
For example:

```json
{
  "error": "Member has an unreturned overdue loan"
}
```

Rejected checkouts leave loan records, inventory, and ID counters unchanged.
Boolean values, decimal numbers, and numeric strings are not accepted as
JSON IDs.

#### Overdue rules

- A loan due today does not block borrowing.
- An unreturned loan blocks borrowing from the first day after its due date.
- The three-day fine grace period does not extend borrowing eligibility.
- Returned loans do not block borrowing.
- Another member's overdue loans do not block borrowing.
- If a member has multiple overdue loans, all must be returned before
  another checkout is allowed.

Dates follow the application's server-local calendar date.

The existing `/ui/loans` form uses the same checkout rules. Successful
submissions redirect to the loans page; rejected submissions display
an error page.



## Tests

Run the complete test suite from the `library-management` directory:

```bash
python -m pytest -v
```

Run the new checkout enhancement tests separately:

```bash
python -m pytest -v tests/test_<name>.py -k enhancement
```
The targeted command selects tests whose names contain `enhancement`.