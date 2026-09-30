from pathlib import Path

import starkbank

from app.batch_reconciliation import find_batch_invoice_ids
from app.batch_store import (
    complete_batch,
    load_batch_payload,
    load_batch_result,
    save_batch_result,
    mark_batch_for_review
)

def recover_confirmed_batch(
    database_path: Path,
    batch_number: int,
) -> str:
    invoice_ids = load_batch_result(database_path, batch_number)

    if invoice_ids is None:
        return "needs_review"

    complete_batch(database_path, batch_number)

    return "completed"

def recover_batch(
    database_path: Path,
    batch_number: int,
    project: starkbank.Project,
) -> str:
    local_result = recover_confirmed_batch(database_path, batch_number)

    if local_result == "completed":
        return "completed"

    drafts = load_batch_payload(database_path, batch_number)

    if drafts is None:
        mark_batch_for_review(database_path, batch_number)
        return "needs_review"

    invoice_ids = find_batch_invoice_ids(
        batch_number,
        drafts,
        project,
    )

    if invoice_ids is None:
        mark_batch_for_review(database_path, batch_number)
        return "needs_review"

    save_batch_result(database_path, batch_number, invoice_ids)
    complete_batch(database_path, batch_number)

    return "completed"