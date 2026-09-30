import sqlite3
from contextlib import closing
from pathlib import Path

def save_event(
    database_path: Path,
    event_id: str,
    content: str,
) -> bool:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor = connection.execute(
                """
                INSERT INTO webhook_events (event_id, content)
                VALUES (?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (event_id, content)
            )

            return cursor.rowcount > 0
        
def list_pending_events(database_path: Path) -> list[tuple[str, str]]:
    if not database_path.is_file():
        return []

    database_uri = database_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'webhook_events'
            """
        ).fetchone()

        if table_exists is None:
            return []

        rows = connection.execute(
            """
            SELECT event_id, content
            FROM webhook_events
            WHERE status = 'pending'
            ORDER BY received_at, event_id
            """
        ).fetchall()

    return rows

def update_event_status(
    database_path: Path,
    event_id: str,
    status: str,
) -> None:
    if status not in ("processed", "ignored"):
        raise ValueError("Status must be processed or ignored")

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE webhook_events
                SET status = ?
                WHERE event_id = ? AND status = 'pending'
                """,
                (status, event_id),
            )

            if cursor.rowcount != 1:
                raise ValueError("Pending event not found")

def mark_event_for_review(
    database_path: Path,
    event_id: str,
    transfer_id: str,
    reason: str,
) -> None:
    if not transfer_id or not reason.strip():
        raise ValueError("Transfer ID and reason are required")

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_reviews (
                    event_id TEXT PRIMARY KEY,
                    transfer_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor = connection.execute(
                """
                UPDATE webhook_events
                SET status = 'needs_review'
                WHERE event_id = ? AND status = 'pending'
                """,
                (event_id,),
            )

            if cursor.rowcount != 1:
                raise ValueError("Pending event not found")

            connection.execute(
                """
                INSERT INTO event_reviews (
                    event_id, transfer_id, reason
                )
                VALUES (?, ?, ?)
                """,
                (event_id, transfer_id, reason),
            )