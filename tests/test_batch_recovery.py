import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.batch_processor import process_batch
from app.batch_recovery import recover_confirmed_batch
from app.batch_store import load_batch_payload, save_batch_schedule
from app.invoices import Customer
from random import Random
from types import SimpleNamespace


def read_status(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT status
            FROM invoice_batches
            WHERE batch_number = 1
            """
        ).fetchone()

    return row[0]


def run_batch(database_path, now):
    return process_batch(
        database_path=database_path,
        batch_number=1,
        now=now,
        customers=[
            Customer(name="Pessoa de Teste", tax_id="00000000000"),
        ],
        rng=Random(42),
        project=object(),
    )


def fake_issue(batch_number, drafts, project):
    return [
        SimpleNamespace(id=f"invoice-{position}")
        for position in range(1, len(drafts) + 1)
    ]


def test_recovery_completes_batch_after_local_completion_failure(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = fake_issue

        with patch("app.batch_processor.complete_batch") as mock_complete:
            mock_complete.side_effect = sqlite3.OperationalError(
                "Database unavailable"
            )

            with pytest.raises(
                sqlite3.OperationalError,
                match="Database unavailable",
            ):
                run_batch(database_path, start_at)

        assert read_status(database_path) == "processing"

        result = recover_confirmed_batch(database_path, 1)

        assert result == "completed"
        assert read_status(database_path) == "completed"
        mock_issue.assert_called_once()


def test_recovery_without_confirmation_preserves_processing_batch(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = RuntimeError("Response unavailable")

        with pytest.raises(RuntimeError, match="Response unavailable"):
            run_batch(database_path, start_at)

        original_payload = load_batch_payload(database_path, 1)

        result = recover_confirmed_batch(database_path, 1)

        mock_issue.assert_called_once()

    assert result == "needs_review"
    assert read_status(database_path) == "processing"
    assert original_payload is not None
    assert load_batch_payload(database_path, 1) == original_payload