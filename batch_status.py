import sqlite3
from contextlib import closing
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    database_path = project_root / "data" / "events.db"

    if not database_path.is_file():
        print("Nenhum planejamento de lotes encontrado.")
        return

    database_uri = database_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'invoice_batches'
            """
        ).fetchone()

        if table_exists is None:
            print("Nenhum planejamento de lotes encontrado.")
            return

        rows = connection.execute(
            """
            SELECT batch_number, scheduled_at, status
            FROM invoice_batches
            ORDER BY batch_number
            """
        ).fetchall()

    if not rows:
        print("Nenhum planejamento de lotes encontrado.")
        return

    for batch_number, scheduled_at, status in rows:
        print(
            f"Lote {batch_number} | "
            f"Horário: {scheduled_at} | "
            f"Status: {status}"
        )

    print(f"\nTotal de lotes: {len(rows)}")


if __name__ == "__main__":
    main()