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