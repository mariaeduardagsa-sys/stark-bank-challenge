import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from random import Random

import starkbank

from app.batch_processor import process_batch, utc_now
from app.batch_store import list_due_batches
from app.invoices import Customer


logger = logging.getLogger(__name__)


def run_due_batches(
    database_path: Path,
    customers: list[Customer],
    rng: Random,
    project: starkbank.Project,
    clock: Callable[[], datetime] = utc_now,
) -> list[tuple[int, str]]:
    due_batches = list_due_batches(database_path, now=clock())
    results = []

    for batch_number, _ in due_batches:
        try:
            status = process_batch(
                database_path=database_path,
                batch_number=batch_number,
                now=clock(),
                customers=customers,
                rng=rng,
                project=project,
                clock=clock,
            )
        except Exception:
            logger.exception(
                "Failed to process batch %s",
                batch_number,
            )
            status = "error"

        results.append((batch_number, status))

    return results