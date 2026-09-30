import starkbank

from app.invoice_issuer import build_starkbank_invoices
from app.invoices import InvoiceDraft


def normalize_tax_id(tax_id: str) -> str:
    return "".join(character for character in tax_id if character.isdigit())


def find_batch_invoice_ids(
    batch_number: int,
    drafts: list[InvoiceDraft],
    project: starkbank.Project,
) -> list[str] | None:
    expected = build_starkbank_invoices(batch_number, drafts)

    found = list(
        starkbank.invoice.query(
            tags=[f"batch-{batch_number}"],
            user=project,
        )
    )

    if len(found) != len(expected):
        return None

    found_ids = [invoice.id for invoice in found]

    if any(
        not isinstance(invoice_id, str) or not invoice_id.strip()
        for invoice_id in found_ids
    ):
        return None

    if len(set(found_ids)) != len(found_ids):
        return None

    ordered_ids = []

    for planned in expected:
        position_tag = planned.tags[-1]

        matches = [
            invoice
            for invoice in found
            if position_tag in (invoice.tags or [])
        ]

        if len(matches) != 1:
            return None

        actual = matches[0]

        if (
            actual.amount != planned.amount
            or actual.name != planned.name
            or normalize_tax_id(actual.tax_id)
            != normalize_tax_id(planned.tax_id)
        ):
            return None

        ordered_ids.append(actual.id)

    if len(set(ordered_ids)) != len(expected):
        return None

    return ordered_ids