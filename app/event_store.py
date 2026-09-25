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