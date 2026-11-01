from datetime import date, timedelta
from app import store

LOAN_PERIOD_DAYS = 14


class CheckoutError(ValueError):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class Loan:
    def __init__(self, id, book_id, member_id, due_date, loan_date=None, return_date=None):
        self.id = id
        self.book_id = book_id
        self.member_id = member_id
        self.loan_date = loan_date or date.today()
        self.due_date = due_date
        self.return_date = return_date

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "member_id": self.member_id,
            "loan_date": self.loan_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
        }
        
    def is_overdue(self, on_date):
        return self.return_date is None and self.due_date < on_date

    @staticmethod
    def default_due_date():
        return date.today() + timedelta(days=LOAN_PERIOD_DAYS)
    
    @classmethod
    def checkout(cls, book_id, member_id):
    # Validate IDs before using them to look up records.
        for field, value in (
            ("book_id", book_id), ("member_id", member_id),
        ):
            if type(value) is not int or value <= 0:
                raise CheckoutError(
                    f"{field} must be a positive integer", 400
                )

        book = store.books.get(book_id)
        if book is None:
            raise CheckoutError("Book not found", 404)

        if member_id not in store.members:
            raise CheckoutError("Member not found", 404)

        if book.available_copies <= 0:
            raise CheckoutError("No copies available", 409)

        checkout_date = date.today()

        has_overdue_loan = any(
            loan.member_id == member_id
            and loan.is_overdue(checkout_date)
            for loan in store.loans.values()
        )

        if has_overdue_loan:
            raise CheckoutError(
                "Member has an unreturned overdue loan", 403
            )

        # All checks have passed. Now change the stored data.
        loan_id = store.next_id("loan")

        loan = cls(
            id=loan_id,
            book_id=book_id,
            member_id=member_id,
            loan_date=checkout_date,
            due_date=checkout_date + timedelta(days=LOAN_PERIOD_DAYS),
        )

        store.loans[loan_id] = loan
        book.available_copies -= 1

        return loan
