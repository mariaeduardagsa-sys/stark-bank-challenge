import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from random import Random
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import starkbank

from app.batch_processor import process_batch
from app.batch_store import load_batch_payload, save_batch_schedule
from app.invoices import Customer


def read_batch_status(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT status
            FROM invoice_batches
            WHERE batch_number = 1
            """
        ).fetchone()

    return row[0]


def run_first_batch(database_path, now):
    return process_batch(
        database_path=database_path,
        batch_number=1,
        now=now,
        customers=[
            Customer(name="Pessoa de Teste", tax_id="00000000000"),
        ],
        rng=Random(42),
        project=object(),
        clock=lambda: now,
    )


def fake_issue(batch_number, drafts, project):
    return [
        SimpleNamespace(id=f"invoice-{position}")
        for position in range(1, len(drafts) + 1)
    ]


def test_process_batch_saves_confirmation_and_completes(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = fake_issue

        result = run_first_batch(database_path, start_at)

        mock_issue.assert_called_once()

    drafts = load_batch_payload(database_path, 1)

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT invoice_ids
            FROM invoice_batch_results
            WHERE batch_number = 1
            """
        ).fetchone()

    assert result == "completed"
    assert read_batch_status(database_path) == "completed"
    assert drafts is not None
    assert json.loads(row[0]) == [
        f"invoice-{position}"
        for position in range(1, len(drafts) + 1)
    ]


def test_process_batch_does_not_send_completed_batch_again(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = fake_issue

        first = run_first_batch(database_path, start_at)
        second = run_first_batch(database_path, start_at)

        mock_issue.assert_called_once()

    assert first == "completed"
    assert second == "skipped"


def test_process_batch_preserves_uncertain_batch_without_resending(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = starkbank.error.UnknownError(
            "Response unavailable"
        )

        with pytest.raises(starkbank.error.UnknownError):
            run_first_batch(database_path, start_at)

        original = load_batch_payload(database_path, 1)

        second = run_first_batch(database_path, start_at)

        mock_issue.assert_called_once()

    assert second == "skipped"
    assert read_batch_status(database_path) == "processing"
    assert original is not None
    assert load_batch_payload(database_path, 1) == original

def test_process_batch_does_not_send_when_preparation_exceeds_deadline(tmp_path):
    database_path = tmp_path / "events.db"
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        result = process_batch(
            database_path=database_path,
            batch_number=1,
            now=start_at,
            customers=[
                Customer(
                    name="Pessoa de Teste",
                    tax_id="00000000000",
                ),
            ],
            rng=Random(42),
            project=object(),
            clock=lambda: start_at + timedelta(hours=3),
        )

        mock_issue.assert_not_called()

    assert result == "missed"
    assert read_batch_status(database_path) == "missed"
    assert load_batch_payload(database_path, 1) is not None