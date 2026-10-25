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