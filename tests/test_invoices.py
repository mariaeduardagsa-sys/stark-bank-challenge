from random import Random

import pytest

from app.invoices import Customer, build_invoice_batch

def test_batch_respects_size_customers_and_amounts():
    customers = [
        Customer(name="Pessoa A", tax_id="00000000000"),
        Customer(name="Pessoa B", tax_id="11111111111"),
    ]

    batch = build_invoice_batch(customers, Random(42))
    
    assert 8 <= len(batch) <= 12

    for invoice in batch:
        assert invoice.customer in customers
        assert isinstance(invoice.amount, int)
        assert 1000 <= invoice.amount <= 10000

def test_batch_rejects_empty_customer_list():
    with pytest.raises(ValueError, match="customers must not be empty"):
        build_invoice_batch([], Random(42))