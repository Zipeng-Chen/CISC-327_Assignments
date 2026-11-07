"""Assignment 3 Member A: success test doubles and baseline-directed behavior tests."""

from datetime import date
from unittest.mock import patch

import pytest

from app import store
from app.models.loan import Loan
from notification_service import get_notifications


@pytest.fixture
def checkout_records(client):
    book = client.post('/books', json={
        'title': 'Clean Code', 'author': 'Robert C. Martin',
        'isbn': 'a3-checkout', 'total_copies': 1,
    }).get_json()
    member = client.post('/members', json={
        'name': 'Alice', 'email': 'alice@example.com',
    }).get_json()
    return book, member


@pytest.fixture
def fixed_checkout_day(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 25)

    monkeypatch.setattr('app.models.loan.date', FixedDate)
    return FixedDate.today()


def assert_saved_checkout(response, book, member):
    assert response.status_code == 201
    assert response.headers['X-Notification-Sent'] == 'true'
    loan = response.get_json()
    assert loan == {
        'id': 1, 'book_id': book['id'], 'member_id': member['id'],
        'loan_date': '2026-12-25', 'due_date': '2027-01-08', 'return_date': None,
    }
    assert store.loans[loan['id']].to_dict() == loan
    assert len(store.loans) == 1
    assert store.books[book['id']].available_copies == 0


def test_checkout_success_stub(client, checkout_records, fixed_checkout_day, monkeypatch):
    """A True-returning stub controls success; assertions verify response and state."""
    monkeypatch.setattr('app.routes.loans.send_notification',
                        lambda recipient, subject, message: True)
    book, member = checkout_records
    response = client.post('/loans', json={'book_id': book['id'], 'member_id': member['id']})
    assert_saved_checkout(response, book, member)
    assert get_notifications() == []


def test_checkout_notification_arguments(client, checkout_records, fixed_checkout_day):
    """Verify the exact interaction and the resulting checkout, including last-copy stock."""
    book, member = checkout_records
    with patch('app.routes.loans.send_notification', return_value=True) as mock_send:
        response = client.post('/loans', json={'book_id': book['id'], 'member_id': member['id']})
    mock_send.assert_called_once_with(
        'alice@example.com', '[Library] Checkout confirmation',
        "Hello Alice, you checked out 'Clean Code' (loan #1). Please return it by 2027-01-08.",
    )
    assert_saved_checkout(response, book, member)
    assert get_notifications() == []


def test_default_due_date_across_year(client, fixed_checkout_day):
    """The default 14-day loan period crosses December into January correctly."""
    assert Loan.default_due_date() == date(2027, 1, 8)
    assert store.loans == {}


@pytest.mark.parametrize('body', [[], 'invalid', 7], ids=['array', 'string', 'number'])
def test_checkout_rejects_non_object_json(client, checkout_records, body):
    """Non-object JSON returns an explanatory error without allocating a loan or changing stock."""
    book, member = checkout_records
    ids_before = store._next_ids.copy()
    response = client.post('/loans', json=body)
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Request body must be a JSON object'}
    assert store.loans == {}
    assert store.books[book['id']].to_dict() == book
    assert store.members[member['id']].to_dict() == member
    assert store._next_ids == ids_before


def test_returned_loan_cannot_be_renewed(client, checkout_records):
    book, member = checkout_records
    loan = Loan(id=store.next_id('loan'), book_id=book['id'], member_id=member['id'],
                loan_date=date(2026, 1, 1), due_date=date(2026, 1, 15),
                return_date=date(2026, 1, 10))
    store.loans[loan.id] = loan
    before = loan.to_dict()
    response = client.put(f'/loans/{loan.id}/renew')
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Loan already returned'}
    assert loan.to_dict() == before
    assert store.books[book['id']].to_dict() == book


def test_unknown_loan_fine_preserves_state(client, checkout_records):
    book, member = checkout_records
    loan = Loan(id=store.next_id('loan'), book_id=book['id'], member_id=member['id'],
                due_date=date(2027, 1, 8), loan_date=date(2026, 12, 25))
    store.loans[loan.id] = loan
    store.books[book['id']].available_copies = 0
    before = loan.to_dict()
    response = client.get('/loans/999/fine')
    assert response.status_code == 404
    assert response.get_json() == {'error': 'Loan not found'}
    assert [item.to_dict() for item in store.loans.values()] == [before]
    assert store.books[book['id']].available_copies == 0


def test_members_page_lists_stored_members(client):
    members = [client.post('/members', json={'name': name, 'email': email}).get_json()
               for name, email in [('Alice', 'alice@example.com'), ('Bob', 'bob@example.com')]]
    response = client.get('/ui/members')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for member in members:
        assert member['name'] in html
        assert member['email'] in html
        assert f'/ui/members/{member["id"]}/delete' in html
    assert [member.to_dict() for member in store.members.values()] == members


def test_member_form_creates_member(client):
    response = client.post('/ui/members', data={'name': 'Carol', 'email': 'carol@example.com'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/ui/members')
    assert len(store.members) == 1
    member = next(iter(store.members.values()))
    assert member.name == 'Carol'
    assert member.email == 'carol@example.com'
    page = client.get(response.headers['Location']).get_data(as_text=True)
    assert 'Carol' in page and 'carol@example.com' in page


def test_member_form_delete_is_idempotent(client):
    first = client.post('/members', json={'name': 'Alice', 'email': 'alice@example.com'}).get_json()
    remaining = client.post('/members', json={'name': 'Bob', 'email': 'bob@example.com'}).get_json()
    for _ in range(2):
        response = client.post(f'/ui/members/{first["id"]}/delete')
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/ui/members')
        assert [member.to_dict() for member in store.members.values()] == [remaining]
    page = client.get('/ui/members').get_data(as_text=True)
    assert 'alice@example.com' not in page
    assert 'bob@example.com' in page
