import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.credits import InvoiceCredit
from app.event_store import save_event
from app.processor import process_event


def make_content(log_type):
    return json.dumps(
        {
            "event": {
                "subscription": "invoice",
                "log": {
                    "type": log_type,
                    "invoice": {
                        "id": "invoice-123",
                        "amount": 1000,
                        "fee": 150,
                    },
                },
            }
        }
    )


def read_status(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT status FROM webhook_events WHERE event_id = ?",
            ("event-123",),
        ).fetchone()

    return row[0]


@pytest.mark.parametrize("log_type", ["created", "paid"])
def test_processor_ignores_non_credit_events(tmp_path, log_type):
    database_path = tmp_path / "events.db"
    content = make_content(log_type)
    save_event(database_path, "event-123", content)

    with patch("app.processor.ensure_transfer") as mock_transfer:
        result = process_event(
            database_path, "event-123", content, object()
        )

    assert result == "ignored"
    assert read_status(database_path) == "ignored"
    mock_transfer.assert_not_called()


def test_processor_finishes_successful_transfer(tmp_path):
    database_path = tmp_path / "events.db"
    content = make_content("credited")
    project = object()
    save_event(database_path, "event-123", content)

    with patch("app.processor.ensure_transfer") as mock_transfer:
        mock_transfer.return_value = SimpleNamespace(
            id="transfer-123",
            status="success",
        )

        result = process_event(
            database_path, "event-123", content, project
        )

        mock_transfer.assert_called_once_with(
            InvoiceCredit(invoice_id="invoice-123", amount=850),
            project,
        )

    assert result == "processed"
    assert read_status(database_path) == "processed"


def test_processor_keeps_unfinished_transfer_pending(tmp_path):
    database_path = tmp_path / "events.db"
    content = make_content("credited")
    save_event(database_path, "event-123", content)

    with patch("app.processor.ensure_transfer") as mock_transfer:
        mock_transfer.return_value = SimpleNamespace(
            id="transfer-123",
            status="created",
        )

        result = process_event(
            database_path, "event-123", content, object()
        )

    assert result == "pending"
    assert read_status(database_path) == "pending"


@pytest.mark.parametrize("status", ["failed", "canceled"])
def test_processor_reports_unsuccessful_transfer(tmp_path, status):
    database_path = tmp_path / "events.db"
    content = make_content("credited")
    save_event(database_path, "event-123", content)

    with patch("app.processor.ensure_transfer") as mock_transfer:
        mock_transfer.return_value = SimpleNamespace(
            id="transfer-123",
            status=status,
        )

        with pytest.raises(RuntimeError, match=f"has status {status}"):
            process_event(
                database_path, "event-123", content, object()
            )

    assert read_status(database_path) == "pending"


def test_processor_preserves_pending_event_when_transfer_raises(tmp_path):
    database_path = tmp_path / "events.db"
    content = make_content("credited")
    save_event(database_path, "event-123", content)

    with patch("app.processor.ensure_transfer") as mock_transfer:
        mock_transfer.side_effect = RuntimeError("Connection unavailable")

        with pytest.raises(RuntimeError, match="Connection unavailable"):
            process_event(
                database_path, "event-123", content, object()
            )

    assert read_status(database_path) == "pending"
    
def test_processor_recovers_after_local_status_update_fails(tmp_path):
    database_path = tmp_path / "events.db"
    content = make_content("credited")
    project = object()

    save_event(database_path, "event-123", content)

    successful_transfer = SimpleNamespace(
        id="transfer-123",
        status="success",
    )

    with (
        patch("app.transfers.find_existing_transfer") as mock_find,
        patch("app.transfers.starkbank.transfer.create") as mock_create,
    ):
        mock_find.side_effect = [None, successful_transfer]
        mock_create.return_value = [successful_transfer]

        with patch("app.processor.update_event_status") as mock_update:
            mock_update.side_effect = sqlite3.OperationalError(
                "Database unavailable"
            )

            with pytest.raises(
                sqlite3.OperationalError,
                match="Database unavailable",
            ):
                process_event(
                    database_path, "event-123", content, project
                )

        assert read_status(database_path) == "pending"

        result = process_event(
            database_path, "event-123", content, project
        )

        assert result == "processed"
        assert read_status(database_path) == "processed"
        assert mock_find.call_count == 2
        mock_create.assert_called_once()