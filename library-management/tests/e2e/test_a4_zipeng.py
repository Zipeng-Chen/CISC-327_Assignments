from uuid import uuid4

from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:5000"


def test_add_book_displays_it_in_the_books_table(page: Page):
    title = f"A4 Book {uuid4().hex[:8]}"

    page.goto(f"{BASE_URL}/ui/books")
    page.get_by_label("Title").fill(title)
    page.get_by_label("Author").fill("Zipeng Chen")
    page.get_by_label("ISBN").fill(uuid4().hex[:13])
    page.get_by_role("button", name="Add Book").click()

    book_row = page.get_by_role("row").filter(has_text=title)
    expect(book_row.get_by_role("cell", name="Zipeng Chen")).to_be_visible()


def test_checkout_rejects_zero_book_id(page: Page):
    page.goto(f"{BASE_URL}/ui/loans")
    page.get_by_label("Book ID").fill("0")
    page.get_by_label("Member ID").fill("1")
    page.get_by_role("button", name="Check Out").click()

    error = page.get_by_text("book_id must be a positive integer", exact=True)
    expect(error).to_be_visible()