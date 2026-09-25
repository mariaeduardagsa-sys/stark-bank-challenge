import sqlite3
from contextlib import closing

from app.event_store import save_event


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