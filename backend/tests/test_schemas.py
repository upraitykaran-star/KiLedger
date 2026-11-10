from datetime import date

import pytest
from pydantic import ValidationError

from backend.schemas import CustomerIn, RegisterIn, TransactionIn


def test_registration_requires_a_long_password():
    with pytest.raises(ValidationError):
        RegisterIn(name="Karan", business_name="Shop", email="karan@example.com", password="short")


def test_transaction_uses_positive_integer_minor_units():
    entry = TransactionIn(description="Sale", amount_minor=12550, type="income", date=date(2026, 10, 28), on_credit=True, customer_id="cust1")
    assert entry.amount_minor == 12550
    assert entry.currency == "INR"


@pytest.mark.parametrize("amount", [0, -1, 1.25])
def test_transaction_rejects_invalid_minor_amount(amount):
    with pytest.raises(ValidationError):
        TransactionIn(description="Sale", amount_minor=amount, type="income", date=date(2026, 10, 28))


def test_payment_cannot_be_on_credit():
    with pytest.raises(ValidationError):
        TransactionIn(description="Payment", amount_minor=100, type="payment", date=date(2026, 10, 28), on_credit=True)


def test_invalid_customer_email_is_rejected():
    with pytest.raises(ValidationError):
        CustomerIn(name="Customer", email="not-an-email")
