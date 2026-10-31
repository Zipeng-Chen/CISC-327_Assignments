import pytest

def test_register_member_returns_created_member(client):
    """
    confirms a member posted to /members is returned with correct fields
    """
    payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    response = client.post("/members", json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert data["name"] == "Alice Smith"
    assert data["email"] == "alice@example.com"
    assert data["id"] == 1

def test_list_members_returns_all_members(client):
    """
    confirms multiple members can be retrieved
    """
    payload1 = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    payload2 = {
        "name" : "Bob Jones",
        "email" : "bob@example.com",
    }

    assert client.post("/members", json=payload1).status_code == 201
    assert client.post("/members", json=payload2).status_code == 201

    response = client.get("/members")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

    assert data[0]["name"] == "Alice Smith"
    assert data[0]["email"] == "alice@example.com"
    assert data[0]["id"] == 1

    assert data[1]["name"] == "Bob Jones"
    assert data[1]["email"] == "bob@example.com"
    assert data[1]["id"] == 2

def test_lookup_id_returns_member(client):
    """
    confirms members can be searched for by their internal id
    """
    payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }

    client.post("/members", json=payload)

    response = client.get("/members/1")
    data = response.get_json()

    assert data["name"] == "Alice Smith"
    assert client.get("/members/999").status_code == 404

def test_updates_member_changes_member_info(client): # its /members/put ... i think ...
    """
    confirms changes to member information updates data accordingly
    """
    payload = {
        "name" : "Bob Jones",
        "email" : "bob@example.com",
    }
    assert client.post("/members", json=payload).status_code == 201
    client.put("/members/1" , json={"name":"Bob Smith"})

    response = client.get("/members/1")
    
    data = response.get_json()
    assert data["name"] == "Bob Smith"
    assert data["email"] == "bob@example.com"
    assert data["id"] == 1

def test_member_deletion_removes_member_info(client):
    """
    confirms deletion of a member removes their data accordingly
    """
    payload = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    assert client.post("/members", json=payload).status_code == 201
    assert client.delete("/members/1").status_code == 204

    response = client.get("/members/1")

    assert response.status_code == 404

def test_loan_renewal_extends_remaining_time(client):
    """
    confirms PUT /loans/<int:loan_id>/renew adds `LOAN_PERIOD_DAYS` to due date
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

    loan_payload = {
        "book_id" : 1,
        "member_id" : 1,
    }
    assert client.post("/loans", json=loan_payload).status_code == 201

    assert client.put("/loans/999/renew", json={}).status_code == 404

    old_date = client.get("/loans?member_id=1&book_id=1").get_json()
    assert client.put("/loans/1/renew").status_code == 200
    new_date = client.get("/loans?member_id=1&book_id=1").get_json()

    assert new_date[0]["due_date"] > old_date[0]["due_date"]

def test_retrieval_of_loans_overdue_fine(client):
    """
    confirms GET /loans/<int:loan_id> retrieves the appropriate information
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

    loan_payload = {
        "book_id" : 1,
        "member_id" : 1,
    }
    assert client.post("/loans", json=loan_payload).status_code == 201

    response = client.get("/loans/1/fine")
    assert response.status_code == 200
    data = response.get_json()

    assert data["fine_amount"] == 0.0

def test_create_reservation_returns_created_reservation(client):
    """
    confirms a reservation posted to /reservations is returned with correct fields
    """
    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 1,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload1 = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    member_payload2 = {
            "name" : "Bob Jones",
            "email" : "bob@example.com",
        }
    assert client.post("/members", json=member_payload1).status_code == 201
    assert client.post("/members", json=member_payload2).status_code == 201

    loan_payload = {
            "book_id" : 1,
            "member_id" : 2,
        }
    assert client.post("/loans", json=loan_payload).status_code == 201

    reservation_payload = {
        "book_id" : 1,
        "member_id" : 1,
    }
    response = client.post("/reservations", json=reservation_payload)
    assert response.status_code == 201

    data = response.get_json()
    assert data["book_id"] == 1
    assert data["member_id"] == 1
    assert data["id"] == 1
    assert data["fulfilled"] == False

def test_list_reservations_returns_all_reservations_under_filter(client):
    """
    confirms multiple reservations can be retrieved and filtered
    """
    book_payload = {
        "title" : "Clean Code",
        "author" : "Robert C. Martin",
        "isbn" : "978-0132350884",
        "total_copies": 2,
    }
    assert client.post("/books", json=book_payload).status_code == 201

    member_payload1 = {
        "name" : "Alice Smith",
        "email" : "alice@example.com",
    }
    member_payload2 = {
            "name" : "Bob Jones",
            "email" : "bob@example.com",
        }
    assert client.post("/members", json=member_payload1).status_code == 201
    assert client.post("/members", json=member_payload2).status_code == 201

    reservation_payload1 = {
        "book_id" : 1,
        "member_id" : 1,
    }
    reservation_payload2 = {
            "book_id" : 1,
            "member_id" : 2,
        }
    client.post("/reservations", json=reservation_payload1)
    client.post("/reservations", json=reservation_payload2)

    response_all = client.get("/reservations").get_json()
    response_alice = client.get("/reservations?member_id=1").get_json()

    assert len(response_all) == 2
    assert response_all[1]["id"] == 2
    assert response_all[1]["book_id"] == 1
    assert response_all[1]["member_id"] == 2

    assert len(response_alice) == 1
    assert response_alice[0]["id"] == 1
    assert response_alice[0]["book_id"] == 1
    assert response_alice[0]["member_id"] == 1

def test_home_page__and_links_return_successfully(client):
    """
    confirms home page loads and link function correctly
    """
    response = client.get("/")

    assert response.status_code == 200