import sqlite3
from contextlib import closing
from unittest.mock import patch

from app.event_runner import run_pending_events
from app.event_store import save_event


def test_runner_handles_database_without_webhook_table(tmp_path):
    database_path = tmp_path / "events.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("CREATE TABLE example (id INTEGER)")

    with patch("app.event_runner.process_event") as mock_process:
        results = run_pending_events(database_path, object())

        mock_process.assert_not_called()

    assert results == []


def test_runner_processes_pending_event(tmp_path):
    database_path = tmp_path / "events.db"
    content = '{"event": {"id": "event-1"}}'
    save_event(database_path, "event-1", content)
    project = object()

    with patch("app.event_runner.process_event") as mock_process:
        mock_process.return_value = "processed"

        results = run_pending_events(database_path, project)

        mock_process.assert_called_once_with(
            database_path,
            "event-1",
            content,
            project,
        )

    assert results == [("event-1", "processed")]


def test_runner_continues_after_event_failure(tmp_path, caplog):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")
    save_event(database_path, "event-2", "{}")

    with patch("app.event_runner.process_event") as mock_process:
        mock_process.side_effect = [
            RuntimeError("Connection unavailable"),
            "ignored",
        ]

        results = run_pending_events(database_path, object())

        assert mock_process.call_count == 2

    assert results == [
        ("event-1", "error"),
        ("event-2", "ignored"),
    ]
    assert "Failed to process event event-1" in caplog.text