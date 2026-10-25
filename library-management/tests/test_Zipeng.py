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