from pathlib import Path

from app.batch_store import complete_batch, load_batch_result


def recover_confirmed_batch(
    database_path: Path,
    batch_number: int,
) -> str:
    invoice_ids = load_batch_result(database_path, batch_number)

    if invoice_ids is None:
        return "needs_review"

    complete_batch(database_path, batch_number)

    return "completed"