import argparse
from pathlib import Path

from app.credits import extract_invoice_credit
from app.event_store import list_pending_events
from app.processor import process_event
from app.stark_client import get_project


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or process pending Sandbox webhook events."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Process events and allow Sandbox transfers.",
    )
    args = parser.parse_args()

    database_path = (
        Path(__file__).resolve().parent / "data" / "events.db"
    )
    events = list_pending_events(database_path)

    print(f"Eventos pendentes: {len(events)}")

    if not events:
        return

    project = get_project() if args.execute else None
    failures = 0

    for event_id, content in events:
        try:
            if not args.execute:
                credit = extract_invoice_credit(content)

                if credit is None:
                    print(f"{event_id}: será ignorado")
                else:
                    print(
                        f"{event_id}: crédito da Invoice {credit.invoice_id} | "
                        f"repasse previsto: {credit.amount} centavos"
                    )

                continue

            result = process_event(
                database_path,
                event_id,
                content,
                project,
            )
            print(f"{event_id}: {result}")

        except Exception as error:
            failures += 1
            print(f"{event_id}: erro: {type(error).__name__}: {error}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()