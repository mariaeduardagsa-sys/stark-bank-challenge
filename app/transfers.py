import starkbank

from app.credits import InvoiceCredit

def build_transfer(credit: InvoiceCredit) -> starkbank.Transfer:
    if not credit.invoice_id:
        raise ValueError("Invoice ID must not be empty")
    
    if type(credit.amount) is not int or credit.amount <= 0:
        raise ValueError("Transfer amount must be a positive integer")
    
    return starkbank.Transfer(
        amount=credit.amount,
        bank_code="20018183",
        branch_code="0001",
        account_number="6341320293482496",
        name="Stark Bank S.A.",
        tax_id="20.018.183/0001-80",
        account_type="payment",
        external_id=f"maria-eduarda-{credit.invoice_id}",
        tags=["challenge", f"maria-eduarda-{credit.invoice_id}"],
    )

def find_existing_transfer(
    credit: InvoiceCredit,
    project: starkbank.Project,
) -> starkbank.Transfer | None:
    expected = build_transfer(credit)

    transfers = starkbank.transfer.query(
        tags=[expected.external_id],
        user=project,
    )

    for transfer in transfers:
        if transfer.external_id != expected.external_id:
            continue

        fields = (
            "amount",
            "bank_code",
            "branch_code",
            "account_number",
            "account_type",
            "tax_id",
        )

        for field in fields:
            if getattr(transfer, field) != getattr(expected, field):
                raise ValueError(
                    f"Existing transfer differs from expected: {field}"
                )

        return transfer

    return None

def ensure_transfer(
    credit: InvoiceCredit,
    project: starkbank.Project,
) -> starkbank.Transfer:
    existing = find_existing_transfer(credit, project)
    
    if existing is not None:
        return existing
    
    transfer = build_transfer(credit)
    
    try:
        created_transfers = starkbank.transfer.create(
            [transfer],
            user = project,
        )
    except starkbank.error.StarkError:
        existing = find_existing_transfer(credit, project)
        
        if existing is not None:
            return existing
        
        raise
    
    return created_transfers[0]