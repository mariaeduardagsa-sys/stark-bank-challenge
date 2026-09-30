import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from random import Random

import starkbank

from app.batch_processor import utc_now
from app.batch_runner import run_due_batches
from app.invoices import Customer


logger = logging.getLogger(__name__)


def run_batch_loop(
    database_path: Path,
    customers: list[Customer],
    rng: Random,
    project: starkbank.Project,
    end_at: datetime,
    interval_seconds: int = 30,
    clock: Callable[[], datetime] = utc_now,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if end_at.tzinfo is None or end_at.utcoffset() is None:
        raise ValueError("end_at must include a timezone")

    if type(interval_seconds) is not int or interval_seconds <= 0:
        raise ValueError("Interval must be a positive integer")

    while clock() < end_at:
        results = run_due_batches(
            database_path=database_path,
            customers=customers,
            rng=rng,
            project=project,
            clock=clock,
        )

        for batch_number, status in results:
            logger.info(
                "Batch %s: %s",
                batch_number,
                status,
            )

        remaining = (end_at - clock()).total_seconds()

        if remaining <= 0:
            break

        sleep(min(interval_seconds, remaining))

    logger.info("Invoice issuance window ended.")