from pathlib import Path

import starkbank

from app.credits import extract_invoice_credit
from app.event_store import mark_event_for_review, update_event_status
from app.transfers import ensure_transfer


def process_event(
    database_path: Path,
    event_id: str,
    content: str,
    project: starkbank.Project,
) -> str:
    credit = extract_invoice_credit(content)

    if credit is None:
        update_event_status(database_path, event_id, "ignored")
        return "ignored"

    transfer = ensure_transfer(credit, project)

    if transfer.status == "success":
        update_event_status(database_path, event_id, "processed")
        return "processed"

    if transfer.status in ("failed", "canceled"):
        mark_event_for_review(
            database_path=database_path,
            event_id=event_id,
            transfer_id=transfer.id,
            reason=f"Transfer has status {transfer.status}",
        )
        return "needs_review"

    return "pending"