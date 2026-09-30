import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.batch_processor import process_batch
from app.batch_recovery import recover_confirmed_batch, recover_batch
from app.batch_store import load_batch_payload, save_batch_schedule, load_batch_result
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
        clock=lambda: now,
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

def prepare_uncertain_batch(database_path):
    start_at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    save_batch_schedule(database_path, start_at)

    with patch("app.batch_processor.issue_invoice_batch") as mock_issue:
        mock_issue.side_effect = RuntimeError("Response unavailable")

        with pytest.raises(RuntimeError, match="Response unavailable"):
            run_batch(database_path, start_at)
            
def test_recover_batch_saves_api_confirmation_and_completes(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_uncertain_batch(database_path)
    drafts = load_batch_payload(database_path, 1)
    project = object()

    invoice_ids = [
        f"invoice-{position}"
        for position in range(1, len(drafts) + 1)
    ]

    with patch("app.batch_recovery.find_batch_invoice_ids") as mock_find:
        mock_find.return_value = invoice_ids

        result = recover_batch(database_path, 1, project)

        mock_find.assert_called_once_with(1, drafts, project)

    assert result == "completed"
    assert read_status(database_path) == "completed"
    assert load_batch_result(database_path, 1) == invoice_ids


def test_recover_batch_preserves_uncertainty_when_api_does_not_match(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_uncertain_batch(database_path)

    with patch("app.batch_recovery.find_batch_invoice_ids") as mock_find:
        mock_find.return_value = None

        result = recover_batch(database_path, 1, object())

    assert result == "needs_review"
    assert read_status(database_path) == "needs_review"
    assert load_batch_result(database_path, 1) is None


def test_recover_batch_preserves_state_when_query_fails(tmp_path):
    database_path = tmp_path / "events.db"
    prepare_uncertain_batch(database_path)

    with patch("app.batch_recovery.find_batch_invoice_ids") as mock_find:
        mock_find.side_effect = RuntimeError("Query unavailable")

        with pytest.raises(RuntimeError, match="Query unavailable"):
            recover_batch(database_path, 1, object())

    assert read_status(database_path) == "processing"
    assert load_batch_result(database_path, 1) is None