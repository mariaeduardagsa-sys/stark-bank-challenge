import pytest

from app.invoice_issuer import (
    build_starkbank_invoices,
    issue_invoice_batch,
)
from app.invoices import Customer, InvoiceDraft

from unittest.mock import patch

import starkbank


def make_drafts(size=8):
    return [
        InvoiceDraft(
            customer=Customer(
                name=f"Pessoa de Teste {index}",
                tax_id="00000000000",
            ),
            amount=1000 + index,
        )
        for index in range(size)
    ]


def test_build_starkbank_invoices_preserves_data_and_adds_tags():
    drafts = make_drafts()

    invoices = build_starkbank_invoices(2, drafts)

    assert len(invoices) == len(drafts)

    for position, (invoice, draft) in enumerate(
        zip(invoices, drafts),
        start=1,
    ):
        assert invoice.amount == draft.amount
        assert invoice.name == draft.customer.name
        assert invoice.tax_id == draft.customer.tax_id
        assert invoice.fine == 0
        assert invoice.interest == 0
        assert invoice.tags == [
            "challenge",
            "batch-2",
            f"batch-2-invoice-{position}",
        ]


def test_build_starkbank_invoices_keeps_tags_stable():
    drafts = make_drafts()

    first = build_starkbank_invoices(1, drafts)
    second = build_starkbank_invoices(1, drafts)

    assert [invoice.tags for invoice in first] == [
        invoice.tags for invoice in second
    ]


@pytest.mark.parametrize("batch_number", [0, -1, True, "1"])
def test_build_starkbank_invoices_rejects_invalid_batch_number(batch_number):
    with pytest.raises(
        ValueError,
        match="Batch number must be a positive integer",
    ):
        build_starkbank_invoices(batch_number, make_drafts())


@pytest.mark.parametrize("size", [7, 13])
def test_build_starkbank_invoices_rejects_invalid_batch_size(size):
    with pytest.raises(
        ValueError,
        match="Batch must contain between 8 and 12 invoices",
    ):
        build_starkbank_invoices(1, make_drafts(size))

def test_issue_invoice_batch_sends_prepared_invoices_once():
    drafts = make_drafts()
    project = object()

    created = build_starkbank_invoices(1, drafts)

    for position, invoice in enumerate(created, start=1):
        invoice.id = f"invoice-{position}"

    with patch("app.invoice_issuer.starkbank.invoice.create") as mock_create:
        mock_create.return_value = created

        result = issue_invoice_batch(1, drafts, project)

        mock_create.assert_called_once()
        sent = mock_create.call_args.args[0]

        assert len(sent) == len(drafts)
        assert mock_create.call_args.kwargs["user"] is project

        for position, (invoice, draft) in enumerate(
            zip(sent, drafts),
            start=1,
        ):
            assert invoice.amount == draft.amount
            assert invoice.name == draft.customer.name
            assert invoice.tax_id == draft.customer.tax_id
            assert f"batch-1-invoice-{position}" in invoice.tags

    assert result is created


def test_issue_invoice_batch_does_not_retry_after_sdk_error():
    error = starkbank.error.UnknownError("Response unavailable")

    with patch("app.invoice_issuer.starkbank.invoice.create") as mock_create:
        mock_create.side_effect = error

        with pytest.raises(starkbank.error.UnknownError) as captured:
            issue_invoice_batch(1, make_drafts(), object())

        mock_create.assert_called_once()

    assert captured.value is error


def test_issue_invoice_batch_does_not_send_invalid_batch():
    with patch("app.invoice_issuer.starkbank.invoice.create") as mock_create:
        with pytest.raises(
            ValueError,
            match="Batch must contain between 8 and 12 invoices",
        ):
            issue_invoice_batch(1, make_drafts(size=7), object())

        mock_create.assert_not_called()