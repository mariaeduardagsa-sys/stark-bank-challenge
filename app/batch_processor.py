from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from random import Random

import starkbank

from app.batch_preparation import prepare_invoice_batch
from app.batch_store import (
    check_batch_send_window,
    claim_batch,
    complete_batch,
    save_batch_result,
)
from app.invoice_issuer import issue_invoice_batch
from app.invoices import Customer


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def process_batch(
    database_path: Path,
    batch_number: int,
    now: datetime,
    customers: list[Customer],
    rng: Random,
    project: starkbank.Project,
    clock: Callable[[], datetime] = utc_now,
) -> str:
    claimed = claim_batch(database_path, batch_number, now)

    if not claimed:
        return "skipped"

    drafts = prepare_invoice_batch(
        database_path,
        batch_number,
        customers,
        rng,
    )

    can_send = check_batch_send_window(
        database_path,
        batch_number,
        now=clock(),
    )

    if not can_send:
        return "missed"

    created = issue_invoice_batch(
        batch_number,
        drafts,
        project,
    )

    invoice_ids = [invoice.id for invoice in created]

    save_batch_result(database_path, batch_number, invoice_ids)
    complete_batch(database_path, batch_number)

    return "completed"