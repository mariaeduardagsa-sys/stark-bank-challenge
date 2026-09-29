import starkbank

from app.invoices import InvoiceDraft


def build_starkbank_invoices(
    batch_number: int,
    invoices: list[InvoiceDraft],
) -> list[starkbank.Invoice]:
    if type(batch_number) is not int or batch_number <= 0:
        raise ValueError("Batch number must be a positive integer")

    if not 8 <= len(invoices) <= 12:
        raise ValueError("Batch must contain between 8 and 12 invoices")

    return [
        starkbank.Invoice(
            amount=invoice.amount,
            name=invoice.customer.name,
            tax_id=invoice.customer.tax_id,
            fine=0,
            interest=0,
            tags=[
                "challenge",
                f"batch-{batch_number}",
                f"batch-{batch_number}-invoice-{position}",
            ],
        )
        for position, invoice in enumerate(invoices, start=1)
    ]

def issue_invoice_batch(
    batch_number: int,
    invoices: list[InvoiceDraft],
    project: starkbank.Project,
) -> list[starkbank.Invoice]:
    prepared = build_starkbank_invoices(batch_number, invoices)

    return starkbank.invoice.create(
        prepared,
        user=project,
    )