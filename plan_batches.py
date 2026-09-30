import argparse
from datetime import datetime
from pathlib import Path

from app.batch_store import save_batch_schedule
from app.schedule import build_batch_schedule


def parse_start_at(value: str) -> datetime:
    try:
        start_at = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Use uma data como 2026-10-01T09:00:00-03:00"
        ) from error

    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            "Informe o fuso horário, por exemplo -03:00."
        )

    return start_at


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Planeja os oito lotes de Invoices do desafio."
    )

    parser.add_argument(
        "--start-at",
        required=True,
        type=parse_start_at,
        help="Data e horário inicial com fuso.",
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="Salva o planejamento no banco local.",
    )

    args = parser.parse_args()

    schedule = build_batch_schedule(args.start_at)

    for number, scheduled_at in enumerate(schedule, start=1):
        print(f"Lote {number}: {scheduled_at.isoformat()}")

    if not args.save:
        print("\nPrévia: nenhum dado foi gravado.")
        return

    project_root = Path(__file__).resolve().parent
    database_path = project_root / "data" / "events.db"

    try:
        saved = save_batch_schedule(database_path, args.start_at)
    except ValueError as error:
        parser.exit(status=1, message=f"\nErro: {error}\n")

    if saved:
        print("\nPlanejamento salvo. Nenhuma Invoice foi enviada.")
    else:
        print("\nEsse planejamento já está salvo.")


if __name__ == "__main__":
    main()