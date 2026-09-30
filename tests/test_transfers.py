import pytest
import starkbank

from app.credits import InvoiceCredit
from unittest.mock import patch
from app.transfers import (
    build_transfer,
    ensure_transfer,
    find_existing_transfer,
)

def test_transfer_uses_net_amount_and_challenge_destination():
    credit = InvoiceCredit(invoice_id="invoice-123", amount=850)

    transfer = build_transfer(credit)

    assert transfer.amount == 850
    assert transfer.bank_code == "20018183"
    assert transfer.branch_code == "0001"
    assert transfer.account_number == "6341320293482496"
    assert transfer.name == "Stark Bank S.A."
    assert transfer.tax_id == "20.018.183/0001-80"
    assert transfer.account_type == "payment"


def test_same_invoice_keeps_same_external_id():
    first_credit = InvoiceCredit(invoice_id="invoice-123", amount=850)
    repeated_credit = InvoiceCredit(invoice_id="invoice-123", amount=850)

    first_transfer = build_transfer(first_credit)
    repeated_transfer = build_transfer(repeated_credit)

    assert first_transfer.external_id == repeated_transfer.external_id
    assert first_transfer.external_id == "maria-eduarda-invoice-123"


def test_different_invoices_have_different_external_ids():
    first_credit = InvoiceCredit(invoice_id="invoice-123", amount=850)
    second_credit = InvoiceCredit(invoice_id="invoice-456", amount=850)

    first_transfer = build_transfer(first_credit)
    second_transfer = build_transfer(second_credit)

    assert first_transfer.external_id != second_transfer.external_id


@pytest.mark.parametrize("amount", [0, -100, 10.5, "850", True])
def test_transfer_rejects_invalid_amount(amount):
    credit = InvoiceCredit(invoice_id="invoice-123", amount=amount)

    with pytest.raises(ValueError):
        build_transfer(credit)


def test_transfer_rejects_empty_invoice_id():
    credit = InvoiceCredit(invoice_id="", amount=850)

    with pytest.raises(ValueError):
        build_transfer(credit)

def test_find_transfer_returns_none_when_not_found():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()

    with patch("app.transfers.starkbank.transfer.query") as mock_query:
        mock_query.return_value = []

        result = find_existing_transfer(credit, project)

        assert result is None

        mock_query.assert_called_once_with(
            tags=["maria-eduarda-123"],
            user=project,
        )


def test_find_transfer_returns_matching_transfer():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    existing = build_transfer(credit)
    existing.id = "transfer-456"

    with patch("app.transfers.starkbank.transfer.query") as mock_query:
        mock_query.return_value = [existing]

        result = find_existing_transfer(credit, project)

        assert result is existing
        assert result.id == "transfer-456"


def test_find_transfer_skips_different_external_id():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()

    unrelated = build_transfer(
        InvoiceCredit(invoice_id="999", amount=850)
    )
    matching = build_transfer(credit)

    with patch("app.transfers.starkbank.transfer.query") as mock_query:
        mock_query.return_value = [unrelated, matching]

        result = find_existing_transfer(credit, project)

        assert result is matching


@pytest.mark.parametrize(
    ("field", "different_value"),
    [
        ("amount", 900),
        ("bank_code", "00000000"),
        ("branch_code", "9999"),
        ("account_number", "123456"),
        ("account_type", "checking"),
        ("tax_id", "00000000000"),
    ],
)
def test_find_transfer_rejects_conflicting_data(field, different_value):
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    existing = build_transfer(credit)

    setattr(existing, field, different_value)

    with patch("app.transfers.starkbank.transfer.query") as mock_query:
        mock_query.return_value = [existing]

        with pytest.raises(
            ValueError,
            match=f"Existing transfer differs from expected: {field}",
        ):
            find_existing_transfer(credit, project)
            
def test_ensure_transfer_reuses_existing_operaation():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    existing = build_transfer(credit)
    
    with (
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        mock_find.return_value = existing
        
        result = ensure_transfer(credit, project)
        
        assert result is existing
        mock_find.assert_called_once_with(credit, project)
        mock_create.assert_not_called()
        
def test_ensure_transfer_creates_when_not_found():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    created = build_transfer(credit)
    created.id = "transfer-456"
    
    with (
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        mock_find.return_value = None
        mock_create.return_value = [created]
        
        result = ensure_transfer(credit, project)
        
        assert result is created
        mock_find.assert_called_once_with(credit, project)
        mock_create.assert_called_once()
        
        sent_transfer = mock_create.call_args.args[0][0]
        
        assert sent_transfer.amount == 850
        assert sent_transfer.external_id == "maria-eduarda-123"
        assert mock_create.call_args.kwargs["user"] is project

def test_ensure_transfer_recovers_operation_after_sdk_error():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    existing = build_transfer(credit)
    existing.id = "transfer-456"
    
    with (
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        mock_find.side_effect = [None, existing]
        mock_create.side_effect = starkbank.error.UnknownError(
            "Response unavailable"
        )
        
        result = ensure_transfer(credit, project)
        
        assert result is existing
        assert mock_find.call_count == 2
        mock_create.assert_called_once()

def test_ensure_transfer_propagates_unresolved_sdk_error():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    error = starkbank.error.UnknownError("Response unavailable")
    
    with(
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        mock_find.side_effect = [None, None]
        mock_create.side_effect = error
        
        with pytest.raises(starkbank.error.UnknownError) as captured:
            ensure_transfer(credit, project)
            
        assert captured.value is error
        assert mock_find.call_count == 2
        mock_create.assert_called_once()
    
def test_ensure_transfer_called_twice():
    credit = InvoiceCredit(invoice_id="123", amount=850)
    project = object()
    
    created = build_transfer(credit)
    created.id = "transfer-456"
    
    with (
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        #primeira consulta: nao existe
        mock_find.side_effect = [None, created]
        mock_create.return_value = [created]
        
        print("------ primeira chamada --------")
        first = ensure_transfer(credit, project)
        
        print("------ segunda chamada --------")
        second = ensure_transfer(credit, project)
        
        assert first is created
        assert second is created
        assert mock_find.call_count == 2
        mock_create.assert_called_once()
        
        print(f"\nChamadas de criação: {mock_create.call_count}")
        
        