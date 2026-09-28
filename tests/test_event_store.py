import sqlite3
from contextlib import closing

import pytest

from app.event_store import (
    list_pending_events,
    mark_event_for_review,
    save_event,
    update_event_status,
)


def test_save_event_persists_new_event(tmp_path):
    database_path = tmp_path / "data" / "events.db"
    content = '{"event": {"id": "event-123"}}'

    saved = save_event(database_path, "event-123", content)

    assert saved is True

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """
            SELECT event_id, content, status
            FROM webhook_events
            WHERE event_id = ?
            """,
            ("event-123",),
        ).fetchone()

    assert row == ("event-123", content, "pending")


def test_save_event_preserves_existing_event(tmp_path):
    database_path = tmp_path / "events.db"
    original_content = '{"event": {"id": "event-123"}}'

    save_event(database_path, "event-123", original_content)

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                UPDATE webhook_events
                SET status = ?
                WHERE event_id = ?
                """,
                ("processed", "event-123"),
            )

    saved_again = save_event(
        database_path,
        "event-123",
        '{"different": "content"}',
    )

    assert saved_again is False

    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute(
            "SELECT event_id, content, status FROM webhook_events"
        ).fetchall()

    assert rows == [("event-123", original_content, "processed")]
    
def test_list_pending_events_returns_empty_when_database_is_missing(tmp_path):
    database_path = tmp_path / "events.db"

    events = list_pending_events(database_path)

    assert events == []
    assert not database_path.exists()


def test_list_pending_events_excludes_finished_events(tmp_path):
    database_path = tmp_path / "events.db"

    save_event(database_path, "event-1", '{"example": 1}')
    save_event(database_path, "event-2", '{"example": 2}')
    save_event(database_path, "event-3", '{"example": 3}')

    update_event_status(database_path, "event-2", "ignored")
    update_event_status(database_path, "event-3", "processed")

    events = list_pending_events(database_path)

    assert events == [("event-1", '{"example": 1}')]


@pytest.mark.parametrize("status", ["processed", "ignored"])
def test_update_event_status_persists_final_status(tmp_path, status):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")

    update_event_status(database_path, "event-1", status)

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT status FROM webhook_events WHERE event_id = ?",
            ("event-1",),
        ).fetchone()

    assert row == (status,)


def test_update_event_status_rejects_invalid_status(tmp_path):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")

    with pytest.raises(ValueError, match="Status must be processed or ignored"):
        update_event_status(database_path, "event-1", "unknown")

    assert list_pending_events(database_path) == [("event-1", "{}")]


def test_update_event_status_rejects_missing_event(tmp_path):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")

    with pytest.raises(ValueError, match="Pending event not found"):
        update_event_status(database_path, "missing-event", "processed")

    assert list_pending_events(database_path) == [("event-1", "{}")]


def test_update_event_status_preserves_finished_event(tmp_path):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")
    update_event_status(database_path, "event-1", "processed")

    with pytest.raises(ValueError, match="Pending event not found"):
        update_event_status(database_path, "event-1", "ignored")

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT status FROM webhook_events WHERE event_id = ?",
            ("event-1",),
        ).fetchone()

    assert row == ("processed",)
    
def test_mark_event_for_review_preserves_details(tmp_path):
    database_path = tmp_path / "events.db"
    save_event(database_path, "event-1", "{}")

    mark_event_for_review(
        database_path,
        event_id="event-1",
        transfer_id="transfer-123",
        reason="Transfer has status failed",
    )

    with closing(sqlite3.connect(database_path)) as connection:
        event = connection.execute(
            """
            SELECT status, content
            FROM webhook_events
            WHERE event_id = ?
            """,
            ("event-1",),
        ).fetchone()

        review = connection.execute(
            """
            SELECT transfer_id, reason
            FROM event_reviews
            WHERE event_id = ?
            """,
            ("event-1",),
        ).fetchone()

    assert event == ("needs_review", "{}")
    assert review == (
        "transfer-123",
        "Transfer has status failed",
    )
    assert list_pending_events(database_path) == []