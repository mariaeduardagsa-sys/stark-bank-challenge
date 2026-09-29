import pytest

from app.batch_payload import (
    deserialize_invoice_batch,
    serialize_invoice_batch,
)
from app.invoices import Customer, InvoiceDraft


def test_batch_serialization_preserves_customers_amounts_and_order():
    invoices = [
        InvoiceDraft(
            customer=Customer(
                name=f"Pessoa de Teste {index}",
                tax_id="00000000000",
            ),
            amount=1000 + index,
        )
        for index in range(8)
    ]

    content = serialize_invoice_batch(invoices)
    restored = deserialize_invoice_batch(content)

    assert restored == invoices


@pytest.mark.parametrize("size", [8, 12])
def test_batch_serialization_accepts_allowed_limits(size):
    invoices = [
        InvoiceDraft(
            customer=Customer(
                name="Pessoa de Teste",
                tax_id="00000000000",
            ),
            amount=1000,
        )
        for _ in range(size)
    ]

    content = serialize_invoice_batch(invoices)

    assert len(deserialize_invoice_batch(content)) == size


@pytest.mark.parametrize("size", [0, 7, 13])
def test_batch_serialization_rejects_invalid_size(size):
    invoices = [
        InvoiceDraft(
            customer=Customer(
                name="Pessoa de Teste",
                tax_id="00000000000",
            ),
            amount=1000,
        )
        for _ in range(size)
    ]

    with pytest.raises(
        ValueError,
        match="Batch must contain between 8 and 12 invoices",
    ):
        serialize_invoice_batch(invoices)