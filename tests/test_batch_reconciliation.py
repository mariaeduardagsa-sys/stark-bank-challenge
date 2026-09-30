from unittest.mock import patch

import pytest
import starkbank

from app.batch_reconciliation import find_batch_invoice_ids
from app.invoice_issuer import build_starkbank_invoices
from app.invoices import Customer, InvoiceDraft


def make_drafts():
    return [
        InvoiceDraft(
            customer=Customer(
                name=f"Pessoa de Teste {index}",
                tax_id="01234567890",
            ),
            amount=1000 + index,
        )
        for index in range(8)
    ]


def make_found_invoices(drafts):
    invoices = build_starkbank_invoices(1, drafts)

    for position, invoice in enumerate(invoices, start=1):
        invoice.id = f"invoice-{position}"
        invoice.tax_id = "012.345.678-90"

    return invoices


def test_reconciliation_matches_positions_and_normalizes_tax_id():
    drafts = make_drafts()
    found = make_found_invoices(drafts)
    project = object()

    with patch("app.batch_reconciliation.starkbank.invoice.query") as query:
        query.return_value = iter(reversed(found))

        result = find_batch_invoice_ids(1, drafts, project)

        query.assert_called_once_with(
            tags=["batch-1"],
            user=project,
        )

    assert result == [
        f"invoice-{position}"
        for position in range(1, 9)
    ]


@pytest.mark.parametrize(
    "problem",
    ["missing", "duplicate", "amount", "customer", "tag"],
)
def test_reconciliation_rejects_inconsistent_results(problem):
    drafts = make_drafts()
    found = make_found_invoices(drafts)

    if problem == "missing":
        found.pop()
    elif problem == "duplicate":
        found[1].id = found[0].id
    elif problem == "amount":
        found[0].amount += 1
    elif problem == "customer":
        found[0].tax_id = "11111111111"
    elif problem == "tag":
        found[0].tags = ["challenge", "batch-1"]

    with patch("app.batch_reconciliation.starkbank.invoice.query") as query:
        query.return_value = iter(found)

        result = find_batch_invoice_ids(1, drafts, object())

    assert result is None


def test_reconciliation_propagates_api_error():
    error = starkbank.error.UnknownError("Response unavailable")

    with patch("app.batch_reconciliation.starkbank.invoice.query") as query:
        query.side_effect = error

        with pytest.raises(starkbank.error.UnknownError) as captured:
            find_batch_invoice_ids(1, make_drafts(), object())

    assert captured.value is error