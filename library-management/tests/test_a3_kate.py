from unittest.mock import patch

# COVERAGE DIRECTED TESTS
def test_coverage_update_missing_member_id(client):
    """
    confirms /members PUT does not throw an exception but returns error message and sets status code to 404 when member_id is missing
    """
    response = client.put("/members/1" , json={"name":"Alice Smith"})

    assert response.get_json()["error"] == "Member not found"
    assert response.status_code == 404

def test_coverage_delete_missing_member_id(client):
    """
    confirms /members DELETE does not throw an exception but returns error message and sets status code to 404 when member_id is missing
    """
    response = client.delete("/members/1" , json={"name":"Alice Smith"})
    
    assert response.get_json()["error"] == "Member not found"
    assert response.status_code == 404

def test_coverage_list_reservations_by_book(client):
    """
    confirms /reservations GET returns correct information when book_id is specified
    """
    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 2,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    assert client.post("/members", json=member_payload).status_code == 201

    reservation_payload = {
        "book_id" : 1,
        "member_id" : 1,
    }
    assert client.post("/reservations", json=reservation_payload).status_code == 201

    response = client.get("/reservations?book_id=1").get_json()

    assert response[0]["id"] == 1
    assert response[0]["book_id"] == 1
    assert response[0]["member_id"] == 1

def test_coverage_create_reservation_missing_book_id(client):
    """
    confirms /reservations POST does not throw an exception but returns error message and sets status code to 404 when book_id is missing
    """
    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 2,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    assert client.post("/members", json=member_payload).status_code == 201

    reservation_payload = {
        "book_id" : None,
        "member_id" : 1,
    }

    response = client.post("/reservations", json=reservation_payload)

    assert response.get_json()["error"] == "Book not found"
    assert response.status_code == 404

def test_coverage_create_reservation_missing_member_id(client):
    """
    confirms /reservations POST does not throw an exception but returns error message and sets status code to 404 when member_id is missing
    """
    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 2,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    assert client.post("/members", json=member_payload).status_code == 201

    reservation_payload = {
        "book_id" : 1,
        "member_id" : None,
    }
    
    response = client.post("/reservations", json=reservation_payload) 

    assert response.get_json()["error"] == "Member not found"
    assert response.status_code == 404

# NOTIFICATION SCENARIO TESTS
def test_notification_failure_to_send_does_not_affect_checkout(client, monkeypatch):

    monkeypatch.setattr(
        "app.routes.loans.send_notification",
        lambda recipient, subject, message: False
    )

    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 1,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    assert client.post("/members", json=member_payload).status_code == 201

    loan_payload = {
            "book_id" : 1,
            "member_id" : 1,
        }
    
    response = client.post("/loans", json=loan_payload)
    assert response.status_code == 201

    assert response.headers["X-Notification-Sent"] == "false"

    assert client.get("/books/1").get_json()["available_copies"] == 0
    assert len(client.get("/loans").get_json()) == 1

def test_notification_rejected_checkout_does_not_send_notification(client):

    with patch("app.routes.loans.send_notification") as mock_send:

        book_payload = {
            "title" : "Clean Code",
            "author" : "Robert C. Martin",
            "isbn" : "978-0132350884",
            "total_copies": 1,
        }
        assert client.post("/books", json=book_payload).status_code == 201

        member_payload = {
            "name" : "Alice Smith",
            "email" : "alice@example.com",
        }
        assert client.post("/members", json=member_payload).status_code == 201

        loan_payload = {
                "book_id" : 999,
                "member_id" : 1,
            }
        
        response = client.post("/loans", json=loan_payload)
        assert response.status_code == 404

        mock_send.assert_not_called()