from pathlib import Path
from random import Random

from app.batch_store import load_batch_payload, save_batch_payload
from app.invoices import Customer, InvoiceDraft, build_invoice_batch


def prepare_invoice_batch(
    database_path: Path,
    batch_number: int,
    customers: list[Customer],
    rng: Random,
) -> list[InvoiceDraft]:
    existing = load_batch_payload(database_path, batch_number)

    if existing is not None:
        return existing

    invoices = build_invoice_batch(customers, rng)

    save_batch_payload(
        database_path,
        batch_number,
        invoices,
    )

    return invoices