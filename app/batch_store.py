import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schedule import build_batch_schedule
from app.batch_payload import (
    deserialize_invoice_batch,
    serialize_invoice_batch,
)
from app.invoices import InvoiceDraft
import json


def save_batch_schedule(
    database_path: Path,
    start_at: datetime,
) -> bool:
    schedule = build_batch_schedule(start_at)

    planned_rows = [
        (number, scheduled_at.astimezone(timezone.utc).isoformat())
        for number, scheduled_at in enumerate(schedule, start=1)
    ]

    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_batches (
                    batch_number INTEGER PRIMARY KEY,
                    scheduled_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )

            existing_rows = connection.execute(
                """
                SELECT batch_number, scheduled_at
                FROM invoice_batches
                ORDER BY batch_number
                """
            ).fetchall()

            if existing_rows:
                if existing_rows != planned_rows:
                    raise ValueError(
                        "A different batch schedule already exists"
                    )

                return False

            connection.executemany(
                """
                INSERT INTO invoice_batches (
                    batch_number, scheduled_at
                )
                VALUES (?, ?)
                """,
                planned_rows,
            )

    return True

def list_pending_batches(
    database_path: Path,
) -> list[tuple[int, datetime]]:
    if not database_path.is_file():
        return []

    database_uri = database_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'invoice_batches'
            """
        ).fetchone()

        if table_exists is None:
            return []

        rows = connection.execute(
            """
            SELECT batch_number, scheduled_at
            FROM invoice_batches
            WHERE status = 'pending'
            ORDER BY scheduled_at, batch_number
            """
        ).fetchall()

    return [
        (batch_number, datetime.fromisoformat(scheduled_at))
        for batch_number, scheduled_at in rows
    ]

def list_due_batches(
    database_path: Path,
    now: datetime,
) -> list[tuple[int, datetime]]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")

    pending_batches = list_pending_batches(database_path)

    return [
        (batch_number, scheduled_at)
        for batch_number, scheduled_at in pending_batches
        if scheduled_at <= now
    ]

def claim_batch(
    database_path: Path,
    batch_number: int,
    now: datetime,
) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")

    database_uri = database_path.resolve().as_uri() + "?mode=rw"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute(
                """
                SELECT scheduled_at, status
                FROM invoice_batches
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if row is None:
                return False

            scheduled_text, status = row

            if status != "pending":
                return False

            scheduled_at = datetime.fromisoformat(scheduled_text)

            if now < scheduled_at:
                return False

            deadline = scheduled_at + timedelta(hours=3)

            if now >= deadline:
                connection.execute(
                    """
                    UPDATE invoice_batches
                    SET status = 'missed'
                    WHERE batch_number = ? AND status = 'pending'
                    """,
                    (batch_number,),
                )

                return False

            cursor = connection.execute(
                """
                UPDATE invoice_batches
                SET status = 'processing'
                WHERE batch_number = ? AND status = 'pending'
                """,
                (batch_number,),
            )

            return cursor.rowcount == 1

def complete_batch(
    database_path: Path,
    batch_number: int,
) -> None:
    database_uri = database_path.resolve().as_uri() + "?mode=rw"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            batch = connection.execute(
                """
                SELECT status
                FROM invoice_batches
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if batch is None or batch[0] != "processing":
                raise ValueError("Processing batch not found")

            table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'invoice_batch_results'
                """
            ).fetchone()

            if table_exists is None:
                raise ValueError("Batch result not found")

            result = connection.execute(
                """
                SELECT invoice_ids
                FROM invoice_batch_results
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if result is None:
                raise ValueError("Batch result not found")

            connection.execute(
                """
                UPDATE invoice_batches
                SET status = 'completed'
                WHERE batch_number = ? AND status = 'processing'
                """,
                (batch_number,),
            )

def save_batch_payload(
    database_path: Path,
    batch_number: int,
    invoices: list[InvoiceDraft],
) -> bool:
    content = serialize_invoice_batch(invoices)
    database_uri = database_path.resolve().as_uri() + "?mode=rw"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            batch = connection.execute(
                """
                SELECT status
                FROM invoice_batches
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if batch is None or batch[0] != "processing":
                raise ValueError("Processing batch not found")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_batch_payloads (
                    batch_number INTEGER PRIMARY KEY,
                    content TEXT NOT NULL
                )
                """
            )

            existing = connection.execute(
                """
                SELECT content
                FROM invoice_batch_payloads
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if existing is not None:
                if existing[0] != content:
                    raise ValueError(
                        "A different payload already exists for this batch"
                    )

                return False

            connection.execute(
                """
                INSERT INTO invoice_batch_payloads (
                    batch_number, content
                )
                VALUES (?, ?)
                """,
                (batch_number, content),
            )

    return True

def load_batch_payload(
    database_path: Path,
    batch_number: int,
) -> list[InvoiceDraft] | None:
    database_uri = database_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'invoice_batch_payloads'
            """
        ).fetchone()

        if table_exists is None:
            return None

        row = connection.execute(
            """
            SELECT content
            FROM invoice_batch_payloads
            WHERE batch_number = ?
            """,
            (batch_number,),
        ).fetchone()

    if row is None:
        return None

    return deserialize_invoice_batch(row[0])

def save_batch_result(
    database_path: Path,
    batch_number: int,
    invoice_ids: list[str],
) -> None:
    if not invoice_ids or any(
        not isinstance(invoice_id, str) or not invoice_id.strip()
        for invoice_id in invoice_ids
    ):
        raise ValueError("Invoice IDs must be non-empty strings")

    if len(set(invoice_ids)) != len(invoice_ids):
        raise ValueError("Invoice IDs must be unique")

    database_uri = database_path.resolve().as_uri() + "?mode=rw"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            row = connection.execute(
                """
                SELECT payload.content
                FROM invoice_batches AS batch
                JOIN invoice_batch_payloads AS payload
                    ON payload.batch_number = batch.batch_number
                WHERE batch.batch_number = ?
                  AND batch.status = 'processing'
                """,
                (batch_number,),
            ).fetchone()

            if row is None:
                raise ValueError("Processing batch with payload not found")

            planned_invoices = deserialize_invoice_batch(row[0])

            if len(invoice_ids) != len(planned_invoices):
                raise ValueError("Invoice count differs from planned batch")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_batch_results (
                    batch_number INTEGER PRIMARY KEY,
                    invoice_ids TEXT NOT NULL
                )
                """
            )

            existing = connection.execute(
                """
                SELECT invoice_ids
                FROM invoice_batch_results
                WHERE batch_number = ?
                """,
                (batch_number,),
            ).fetchone()

            if existing is not None:
                if set(json.loads(existing[0])) != set(invoice_ids):
                    raise ValueError("A different batch result already exists")

                return

            connection.execute(
                """
                INSERT INTO invoice_batch_results (
                    batch_number, invoice_ids
                )
                VALUES (?, ?)
                """,
                (batch_number, json.dumps(invoice_ids)),
            )

def load_batch_result(
    database_path: Path,
    batch_number: int,
) -> list[str] | None:
    database_uri = database_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'invoice_batch_results'
            """
        ).fetchone()

        if table_exists is None:
            return None

        row = connection.execute(
            """
            SELECT invoice_ids
            FROM invoice_batch_results
            WHERE batch_number = ?
            """,
            (batch_number,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row[0])