import json

import pytest

from app.credits import InvoiceCredit, extract_invoice_credit


def make_event_content(
    log_type="credited",
    amount=1000,
    fee=0,
    subscription="invoice",
):
    return json.dumps(
        {
            "event": {
                "subscription": subscription,
                "log": {
                    "type": log_type,
                    "invoice": {
                        "id": "invoice-123",
                        "amount": amount,
                        "fee": fee,
                    },
                },
            }
        }
    )


def test_credit_subtracts_invoice_fee():
    content = make_event_content(amount=1000, fee=150)

    credit = extract_invoice_credit(content)

    assert credit == InvoiceCredit(
        invoice_id="invoice-123",
        amount=850,
    )


def test_credit_accepts_zero_fee():
    content = make_event_content(amount=1000, fee=0)

    credit = extract_invoice_credit(content)

    assert credit.amount == 1000


@pytest.mark.parametrize("log_type", ["created", "paid", "canceled", "unknown"])
def test_non_credit_events_are_ignored(log_type):
    content = make_event_content(log_type=log_type)

    assert extract_invoice_credit(content) is None


def test_other_subscriptions_are_ignored():
    content = json.dumps({"event": {"subscription": "transfer"}})

    assert extract_invoice_credit(content) is None


@pytest.mark.parametrize(
    ("amount", "fee"),
    [
        ("1000", 0),
        (1000, "10"),
        (1000.5, 0),
        (True, 0),
        (1000, False),
        (-1000, 0),
        (1000, -10),
        (0, 0),
        (1000, 1000),
        (1000, 1100),
    ],
)
def test_invalid_credit_values_are_rejected(amount, fee):
    content = make_event_content(amount=amount, fee=fee)

    with pytest.raises(ValueError):
        extract_invoice_credit(content)


def test_missing_fee_is_not_assumed_to_be_zero():
    data = json.loads(make_event_content())
    del data["event"]["log"]["invoice"]["fee"]

    with pytest.raises(KeyError):
        extract_invoice_credit(json.dumps(data))