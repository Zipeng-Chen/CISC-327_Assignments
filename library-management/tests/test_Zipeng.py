""" Existing-feature tests for Assignment 2, Step 2.

Contributor: Zipeng Chen
Use the supplied client fixture; each test starts with a fresh in-memory store.
Requirement-based defect tests are deliberately left as ordinary assertions.
They should not be weakened to accept incorrect application behaviour.

"""


from datetime import date, timedelta

import pytest

from app import store
from app.models.loan import LOAN_PERIOD_DAYS

def _create_book(client, **changes):
    payload = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 2,
    }
    payload.update(changes)
    response = client.post("/books", json=payload)
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def _book_record(book_id, payload):
    return {"id": book_id, **payload, "available_copies": payload["total_copies"]}

# Feature 1: Add a book.
# Tests book creation, default values, input validation, and HTML form submission.
# Book fields are defined in the README (no standalone Table A requirement)

def test_add_book_stores_all_fields_and_assigns_distinct_ids(client):
    # Create two books and verify their information is saved correctly.
    first = _create_book(client)
    second = _create_book(client, title="Gardening", isbn="garden-1", total_copies=3)

    # Check required fields and initial available copies
    assert first == {
        "id": first["id"],
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 2,
        "available_copies": 2,
    }

    # Each book should have a unique ID and correct copy counts
    assert first["id"] != second["id"]
    assert second["title"] == "Gardening"
    assert second["total_copies"] == second["available_copies"] == 3

    # Confirm both books can be retrieved with their saved information.
    assert client.get(f"/books/{first['id']}").get_json() == first
    assert client.get(f"/books/{second['id']}").get_json() == second


def test_add_book_defaults_to_one_available_copy(client):
    # Verify that omitted total_copies defaults to 1.
    payload = {"title": "Default Copy", "author": "A", "isbn": "default-1"}
    response = client.post("/books", json=payload)

    assert response.status_code == 201
    saved = response.get_json()

    # Both total and available copies should default to 1
    assert saved == {"id": saved["id"], **payload,
                     "total_copies": 1, "available_copies": 1}

    # Confirm the default values are stored.
    assert client.get(f"/books/{saved['id']}").get_json() == saved


@pytest.mark.parametrize("missing_field", ["title", "author", "isbn"])
def test_add_book_rejects_missing_required_field_without_creating_record(client, missing_field):
    # Test each missing required field separately using parametrization.
    existing = _create_book(client)
    payload = {"title": "Incomplete", "author": "A", "isbn": "missing-1"}
    del payload[missing_field]

    # Convert unhandled exceptions into HTTP 500 for clearer test failures
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    response = client.post("/books", json=payload)

    # Invalid requests should return HTTP 4xx, not a server error
    assert 400 <= response.status_code < 500, "Missing fields need a client-validation error"

    # Rejected requests must not create additional books
    assert client.get("/books").get_json() == [existing]


@pytest.mark.parametrize("total_copies", [0, 1])
def test_add_book_initialises_zero_or_one_copy_consistently(client, total_copies):
    # Test boundary values: zero and one copy through the JSON API
    saved = _create_book(client, total_copies=total_copies)
    actual = client.get(f"/books/{saved['id']}").get_json()

    # All copies should initially be available, even when stock is zero
    assert actual["total_copies"] == actual["available_copies"] == total_copies
    assert actual["title"] == saved["title"]


def test_add_book_form_saves_fields_and_displays_created_record(client):
    # Submit a book through the HTML form.
    payload = {"title": "Form Book", "author": "Form Author", "isbn": "form-1", "total_copies": "3"}
    response = client.post("/ui/books", data=payload, follow_redirects=True)

    assert response.status_code == 200

    # Verify the form data is saved and the copy count is converted to an integer
    saved, = client.get("/books").get_json()
    assert saved == _book_record(saved["id"], {**payload, "total_copies": 3})

    # Confirm the created book appears on the resulting HTML page
    html = response.get_data(as_text=True)
    assert all(value in html for value in ["Form Book", "Form Author", "form-1"])
    
    
    
# Feature 2: List all books, including their stored availability (R3, partial).
# tests that all books are displayed correctly without modifying stored data.

def test_list_books_returns_every_record_without_changing_state(client):
    # Create three books with different titles, ISBNs, and copy counts
    expected = [_create_book(client, title=f"Book {n}", isbn=f"isbn-{n}", total_copies=n)
                for n in range(1, 4)]

    # Retrieve all books and verify the response contains every record
    response = client.get("/books")
    assert response.status_code == 200
    assert sorted(response.get_json(), key=lambda book: book["id"]) == expected

    # Repeated GET requests should return the same data without changes.
    assert client.get("/books").get_json() == response.get_json()


def test_books_page_displays_all_books_and_inventory_headings(client):
    # Create two books to verify their visibility on the HTML page
    first = _create_book(client, title="First Catalogue Book")
    second = _create_book(client, title="Second Catalogue Book", isbn="second-1")

    # Retrieve the books page and check that both titles are displayed
    response = client.get("/ui/books")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert first["title"] in html and second["title"] in html

    # Verify the page includes inventory column headings
    assert "<th>Total</th>" in html and "<th>Available</th>" in html

    # Viewing the page should not modify the stored books
    assert client.get("/books").get_json() == [first, second]
    
# Feature 3: Search by title or author (R1, R2)
# Tests case-insensitive search, partial matching, result ordering, and no-match cases.

@pytest.mark.parametrize("query", ["cLeAn", "mArTiN", "Code Hand"])
def test_search_books_matches_partial_title_or_author_case_insensitively(client, query):
    # Test different search terms and capitalization for title and author
    match = _create_book(client, title="Clean Code Handbook")
    other = _create_book(client, title="Gardening", author="Jane Green", isbn="garden-2")

    # Verify that only the matching book is returned
    response = client.get("/books", query_string={"search": query})
    assert response.status_code == 200
    assert response.get_json() == [match]

    # Searching should not modify the original book catalogue
    assert client.get("/books").get_json() == [match, other]


def test_search_books_returns_all_matching_records_and_excludes_unrelated_books(client):
    # Create two matching books and one unrelated book.
    first = _create_book(client, title="Clean Code Handbook")
    exact = _create_book(client, title="Clean Code", isbn="exact-1")
    _create_book(client, title="Gardening", author="Jane Green", isbn="garden-3")

    # Verify that all matching books are returned, excluding unrelated records
    response = client.get("/books", query_string={"search": "clean"})
    assert response.status_code == 200
    assert {book["id"] for book in response.get_json()} == {first["id"], exact["id"]}


def test_search_books_places_exact_title_before_earlier_partial_match(client):
    # R2: Exact title matches should appear before partial matches
    partial = _create_book(client, title="Clean Code Handbook")
    exact = _create_book(client, title="Clean Code", isbn="exact-2")

    # Verify correct ordering even when the partial match was created first.
    response = client.get("/books", query_string={"search": "Clean Code"})
    assert response.status_code == 200
    assert [book["id"] for book in response.get_json()] == [exact["id"], partial["id"]]


def test_search_books_places_exact_author_before_partial_author_match(client):
    # R2: Exact author matches should also appear before partial matches
    partial = _create_book(client, author="Martin Fowler")
    exact = _create_book(client, title="Other Book", author="Martin", isbn="author-1")

    # Verify that the exact author match appears first
    response = client.get("/books", query_string={"search": "Martin"})
    assert response.status_code == 200
    assert [book["id"] for book in response.get_json()] == [exact["id"], partial["id"]]


def test_search_books_no_match_is_empty_and_preserves_catalogue(client):
    # Search for a title that does not exist in the catalogue
    book = _create_book(client)
    response = client.get("/books", query_string={"search": "NoSuchTitle"})

    # Verify that no results are returned and no books are modified
    assert response.status_code == 200
    assert response.get_json() == []
    assert client.get("/books").get_json() == [book]
    
# Feature 4: View one book's details (R3, supported fields)
# Tests retrieving a specific book and handling invalid book IDs

def test_get_book_returns_selected_record_with_complete_stored_details(client):
    # Create two books and retrieve the second one by its ID.
    first = _create_book(client)
    second = _create_book(client, title="Selected Book", isbn="selected-1", total_copies=4)
    response = client.get(f"/books/{second['id']}")

    # Verify the correct book is returned with all its stored details.
    assert response.status_code == 200
    assert response.get_json() == second
    assert response.get_json()["id"] != first["id"]


def test_get_unknown_book_returns_error_without_altering_catalogue(client):
    # Request a non-existent book ID.
    existing = _create_book(client)
    response = client.get("/books/9999")

    # Verify HTTP 404 and the expected error message.
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book not found"}

    # Invalid requests should not modify the existing catalogue.
    assert client.get("/books").get_json() == [existing]


# Feature 5: Update a book (existing README operation; no direct Table A match).
# Tests full updates, partial updates, and handling invalid book IDs.

def test_update_book_persists_changed_fields_and_keeps_other_book_unchanged(client):
    # Create two books and prepare updated information for the first one.
    book = _create_book(client)
    other = _create_book(client, title="Unchanged Book", isbn="unchanged-1")
    changes = {"title": "Revised Title", "author": "Revised Author", "isbn": "revised-1",
               "total_copies": 5, "available_copies": 4}

    # Update the first book using PUT.
    response = client.put(f"/books/{book['id']}", json=changes)

    # Verify the updated fields are saved correctly.
    assert response.status_code == 200
    assert response.get_json() == {**book, **changes}
    assert client.get(f"/books/{book['id']}").get_json() == {**book, **changes}

    # Updating one book should not affect other books.
    assert client.get(f"/books/{other['id']}").get_json() == other


def test_partial_book_update_preserves_omitted_fields_and_search_uses_new_title(client):
    # Create a book and update only its title.
    book = _create_book(client, title="Original Unique Title")
    response = client.put(f"/books/{book['id']}", json={"title": "Revised Unique Title"})
    expected = {**book, "title": "Revised Unique Title"}

    # Verify the new title is saved while other fields remain unchanged.
    assert response.status_code == 200
    assert response.get_json() == expected
    assert client.get(f"/books/{book['id']}").get_json() == expected

    # Search should use the updated title, not the original one.
    assert client.get("/books", query_string={"search": "Original Unique"}).get_json() == []
    assert client.get("/books", query_string={"search": "Revised Unique"}).get_json() == [expected]


def test_update_unknown_book_returns_error_without_creating_record(client):
    # Attempt to update a book that does not exist
    existing = _create_book(client)
    response = client.put("/books/9999", json={"title": "Ghost"})

    # Verify HTTP 404 and the expected error message.
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book not found"}

    # Failed updates should not create or modify any books.
    assert client.get("/books").get_json() == [existing]
    
# Feature 6: Delete a book (existing README operation; no direct Table A match).
# Tests successful deletion, invalid IDs, repeated deletion, and HTML form deletion.

def test_delete_book_removes_only_target_from_lookup_list_and_search(client):
    # Create two books and delete only the target book.
    target = _create_book(client, title="Delete This Unique Title")
    other = _create_book(client, title="Keep This Book", isbn="keep-1")
    response = client.delete(f"/books/{target['id']}")

    # Verify successful deletion (204 No Content).
    assert response.status_code == 204
    assert response.data == b""

    # Deleted book should disappear from lookup, catalogue, and search.
    assert client.get(f"/books/{target['id']}").status_code == 404
    assert client.get("/books").get_json() == [other]
    assert client.get("/books", query_string={"search": "Delete This"}).get_json() == []


def test_delete_unknown_book_returns_error_and_preserves_existing_book(client):
    # Attempt to delete a non-existent book.
    existing = _create_book(client)
    response = client.delete("/books/9999")

    # Verify HTTP 404 and the expected error message.
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book not found"}

    # Failed deletion should not affect existing books.
    assert client.get("/books").get_json() == [existing]


def test_delete_book_twice_does_not_remove_another_book(client):
    # Create two books and successfully delete the first one.
    target = _create_book(client)
    other = _create_book(client, title="Keep After Repeat", isbn="keep-2")
    assert client.delete(f"/books/{target['id']}").status_code == 204

    # Deleting the same book again should return HTTP 404.
    response = client.delete(f"/books/{target['id']}")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Book not found"}

    # Repeated deletion must not affect the remaining book.
    assert client.get("/books").get_json() == [other]


def test_delete_book_form_removes_target_and_redirects_to_updated_catalogue(client):
    # Create two books and delete the target through the HTML form.
    target = _create_book(client, title="Form Deletion Target")
    other = _create_book(client, title="Form Deletion Survivor", isbn="keep-3")
    response = client.post(f"/ui/books/{target['id']}/delete", follow_redirects=True)

    # Verify successful navigation and updated catalogue.
    assert response.status_code == 200
    assert client.get("/books").get_json() == [other]

    # Confirm only the remaining book appears on the resulting page.
    html = response.get_data(as_text=True)
    assert target["title"] not in html
    assert other["title"] in html


# Helper: Create a library member for loan-related tests.
def _create_member(client, name="Alice"):
    response = client.post("/members", json={"name": name, "email": f"{name.lower()}@example.test"})

    # Verify successful member creation and return the saved record.
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


# Helper: Check out a book to a member through the JSON API.
def _checkout(client, book_id, member_id):
    response = client.post("/loans", json={"book_id": book_id, "member_id": member_id})

    # Verify the loan was created successfully.
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


# Helper: Submit checkout requests through either the HTML form or JSON API.
def _submit_checkout(client, book_id, member_id, via_form):
    payload = {"book_id": book_id, "member_id": member_id}

    # Use form submission when via_form=True; otherwise use the JSON API.
    if via_form:
        return client.post("/ui/loans", data=payload, follow_redirects=True)
    return client.post("/loans", json=payload)


@pytest.fixture
def assessment_day(monkeypatch):
    # Freeze the application date for consistent, reproducible loan tests.
    fixed_day = date(2026, 10, 21)

    # Override date.today() to return the fixed test date.
    class FixedDate(date):
        @classmethod
        def today(cls):
            return fixed_day

    # Apply the fixed date to the relevant application modules.
    # This does not change the computer's actual date.
    monkeypatch.setattr("app.models.loan.date", FixedDate)
    monkeypatch.setattr("app.routes.loans.date", FixedDate)
    monkeypatch.setattr("app.routes.views.date", FixedDate)
    return fixed_day

# Feature 7: Check out a book (R4, R7, R16; queue interpretation from R9)
# Tests loan creation, inventory updates, borrower eligibility, and reservation priority

def test_checkout_records_member_book_dates_and_decrements_stock(client, assessment_day):
    # Create a book and member, then check out the book
    book = _create_book(client)
    member = _create_member(client)
    response = client.post("/loans", json={"book_id": book["id"], "member_id": member["id"]})

    # Verify successful checkout with correct loan details and dates
    assert response.status_code == 201
    loan = response.get_json()
    assert loan == {
        "id": loan["id"], "book_id": book["id"], "member_id": member["id"],
        "loan_date": assessment_day.isoformat(),
        "due_date": (assessment_day + timedelta(days=LOAN_PERIOD_DAYS)).isoformat(),
        "return_date": None,
    }

    # Confirm the loan is saved and available copies decrease by one
    assert client.get("/loans").get_json() == [loan]
    assert client.get(f"/books/{book['id']}").get_json() == {**book, "available_copies": 1}


def test_checkout_form_creates_dated_loan_and_displays_return_action(client, assessment_day):
    # Submit checkout through the HTML form
    book = _create_book(client)
    member = _create_member(client)
    response = _submit_checkout(client, book["id"], member["id"], via_form=True)

    # Verify the loan contains correct book, member, and date information
    assert response.status_code == 200
    loan, = client.get("/loans").get_json()
    assert loan["book_id"] == book["id"] and loan["member_id"] == member["id"]
    assert loan["loan_date"] == assessment_day.isoformat()
    assert loan["due_date"] == (assessment_day + timedelta(days=LOAN_PERIOD_DAYS)).isoformat()
    assert loan["return_date"] is None

    # Confirm inventory decreases and the page displays a return action
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 1
    assert f"/ui/loans/{loan['id']}/return" in response.get_data(as_text=True)


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
def test_checkout_last_available_copy_succeeds_and_leaves_zero_stock(client, via_form):
    # Test checkout of the last available copy through API and HTML form
    book = _create_book(client, total_copies=1)
    member = _create_member(client)
    response = _submit_checkout(client, book["id"], member["id"], via_form)

    # Verify successful checkout and zero remaining stock
    assert response.status_code == (200 if via_form else 201)
    loan, = client.get("/loans").get_json()
    assert loan["book_id"] == book["id"] and loan["member_id"] == member["id"]
    assert client.get(f"/books/{book['id']}").get_json() == {**book, "available_copies": 0}


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
def test_checkout_rejects_exhausted_stock_without_extra_loan_or_negative_inventory(client, via_form):
    # R7: Prevent checkout when all copies are already borrowed
    book = _create_book(client, total_copies=1)
    member = _create_member(client)
    first_loan = _checkout(client, book["id"], member["id"])

    # Attempt another checkout with no available stock
    response = _submit_checkout(client, book["id"], member["id"], via_form)
    if not via_form:
        assert 400 <= response.status_code < 500, "Checkout must reject exhausted stock"

    # Verify no extra loan is created and inventory remains at zero
    assert client.get("/loans").get_json() == [first_loan]
    assert client.get(f"/books/{book['id']}").get_json() == {**book, "available_copies": 0}


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
def test_checkout_unknown_book_leaves_inventory_and_loans_unchanged(client, via_form):
    # Attempt checkout using a non-existent book ID
    existing = _create_book(client)
    member = _create_member(client)
    response = _submit_checkout(client, 9999, member["id"], via_form)

    # Verify the API returns HTTP 404 for an unknown book
    if not via_form:
        assert response.status_code == 404
        assert response.get_json() == {"error": "Book not found"}

    # Confirm no loans are created and existing books remain unchanged
    assert client.get("/loans").get_json() == []
    assert client.get("/books").get_json() == [existing]


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
def test_checkout_rejects_nonexistent_member_without_changing_stock(client, via_form):
    # R7: Reject checkout requests from non-existent members
    book = _create_book(client)
    response = _submit_checkout(client, book["id"], 9999, via_form)

    # Verify the API rejects the invalid member ID
    if not via_form:
        assert 400 <= response.status_code < 500, "Checkout needs an existing member"

    # Confirm no loan is created and inventory remains unchanged
    assert client.get("/loans").get_json() == []
    assert client.get(f"/books/{book['id']}").get_json() == book


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
@pytest.mark.parametrize("days_overdue", [1, 4])
def test_checkout_blocks_overdue_borrower_even_during_fine_grace_period(
    client, assessment_day, via_form, days_overdue
):
    # R16: Block checkout for borrowers with overdue loans
    # Test 1-day and 4-day overdue cases through API and HTML form
    book = _create_book(client, total_copies=3)
    member = _create_member(client)
    previous = _checkout(client, book["id"], member["id"])

    # Modify the due date directly because the public API cannot update it
    store.loans[previous["id"]].due_date = assessment_day - timedelta(days=days_overdue)
    before_loans = client.get("/loans").get_json()
    before_book = client.get(f"/books/{book['id']}").get_json()

    # Attempt checkout while the borrower has an overdue loan
    response = _submit_checkout(client, book["id"], member["id"], via_form)
    if not via_form:
        assert 400 <= response.status_code < 500, "R16 requires overdue borrowers to be blocked"

    # Verify rejected checkout does not change loans or inventory
    assert client.get("/loans").get_json() == before_loans
    assert client.get(f"/books/{book['id']}").get_json() == before_book


def test_checkout_accepts_borrower_whose_existing_loan_is_due_today(client, assessment_day):
    # A loan due today is not overdue, so another checkout should be allowed
    book = _create_book(client, total_copies=3)
    member = _create_member(client)
    first = _checkout(client, book["id"], member["id"])
    store.loans[first["id"]].due_date = assessment_day

    # Verify a second loan can be created for the same member
    second = _checkout(client, book["id"], member["id"])
    loans = client.get("/loans").get_json()
    assert {loan["id"] for loan in loans} == {first["id"], second["id"]}
    assert all(loan["member_id"] == member["id"] for loan in loans)

    # Both checkouts should reduce available copies from three to one
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 1


def test_checkout_accepts_borrower_after_overdue_loan_has_been_returned(client, assessment_day):
    # Create an overdue loan and return it before another checkout
    book = _create_book(client, total_copies=1)
    member = _create_member(client)
    first = _checkout(client, book["id"], member["id"])
    store.loans[first["id"]].due_date = assessment_day - timedelta(days=4)

    # Return the overdue book to remove the borrowing restriction
    returned = client.put(f"/loans/{first['id']}/return")
    assert returned.status_code == 200

    # Verify the member can successfully borrow again
    second = _checkout(client, book["id"], member["id"])
    loans = {loan["id"]: loan for loan in client.get("/loans").get_json()}

    # Confirm the first loan is returned and the second remains active
    assert loans[first["id"]]["return_date"] == assessment_day.isoformat()
    assert loans[second["id"]]["return_date"] is None
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 0


@pytest.mark.parametrize("via_form", [False, True], ids=["api", "form"])
def test_checkout_cannot_bypass_waiting_member_after_reserved_book_is_returned(client, via_form):
    # R9: Waiting members should have priority when reserved books are returned
    book = _create_book(client, total_copies=1)
    borrower = _create_member(client)
    waiter = _create_member(client, "Bob")
    first = _checkout(client, book["id"], borrower["id"])

    # Create a reservation for another member while the book is borrowed
    reservation_response = client.post(
        "/reservations", json={"book_id": book["id"], "member_id": waiter["id"]}
    )
    assert reservation_response.status_code == 201
    reservation = reservation_response.get_json()

    # Return the book and attempt checkout by the original borrower
    assert client.put(f"/loans/{first['id']}/return").status_code == 200
    before_loans = client.get("/loans").get_json()
    response = _submit_checkout(client, book["id"], borrower["id"], via_form)

    # Verify checkout cannot bypass the waiting member
    if not via_form:
        assert 400 <= response.status_code < 500, "The waiting member must have priority"

    # Confirm loans, inventory, and reservation remain unchanged
    assert client.get("/loans").get_json() == before_loans
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 1
    assert client.get("/reservations").get_json() == [reservation]


# Helper: Submit book returns through either the HTML form or JSON API
def _submit_return(client, loan_id, via_form):
    # Use the HTML endpoint when via_form=True, otherwise use the API
    if via_form:
        return client.post(f"/ui/loans/{loan_id}/return", follow_redirects=True)
    return client.put(f"/loans/{loan_id}/return")

