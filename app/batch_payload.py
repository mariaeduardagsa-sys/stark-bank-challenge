import json

from app.invoices import Customer, InvoiceDraft


def serialize_invoice_batch(invoices: list[InvoiceDraft]) -> str:
    if not 8 <= len(invoices) <= 12:
        raise ValueError("Batch must contain between 8 and 12 invoices")

    payload = [
        {
            "name": invoice.customer.name,
            "tax_id": invoice.customer.tax_id,
            "amount": invoice.amount,
        }
        for invoice in invoices
    ]

    return json.dumps(payload, ensure_ascii=False)


def deserialize_invoice_batch(content: str) -> list[InvoiceDraft]:
    payload = json.loads(content)

    return [
        InvoiceDraft(
            customer=Customer(
                name=item["name"],
                tax_id=item["tax_id"],
            ),
            amount=item["amount"],
        )
        for item in payload
    ]