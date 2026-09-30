import argparse
import logging
from datetime import timedelta
from pathlib import Path
from random import Random

from app.batch_processor import utc_now
from app.batch_runner import run_due_batches
from app.batch_store import list_pending_batches, load_schedule_end
from app.batch_worker import run_batch_loop
from app.customers import build_sandbox_customers
from app.stark_client import get_project


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consulta ou executa os lotes de Invoices."
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa uma rodada de emissão no Sandbox.",
    )
    
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Repete as rodadas até o fim das 24 horas.",
    )

    args = parser.parse_args()
    
    if args.watch and not args.execute:
        parser.error("--watch exige --execute")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    project_root = Path(__file__).resolve().parent
    database_path = project_root / "data" / "events.db"

    pending = list_pending_batches(database_path)

    if not pending:
        print(
            "Nenhum lote pendente. Use batch_status.py "
            "para conferir o planejamento."
        )
        return

    now = utc_now()

    for batch_number, scheduled_at in pending:
        deadline = scheduled_at + timedelta(hours=3)

        if now < scheduled_at:
            situation = "aguardando horário"
        elif now >= deadline:
            situation = "prazo vencido; será marcado como missed"
        else:
            situation = "dentro da janela de execução"

        print(
            f"Lote {batch_number} | "
            f"Horário: {scheduled_at.isoformat()} | "
            f"{situation}"
        )

    if not args.execute:
        print("\nPrévia: nenhuma Invoice foi enviada.")
        return

    project = get_project()
    customers = build_sandbox_customers()

    results = run_due_batches(
        database_path=database_path,
        customers=customers,
        rng=Random(),
        project=project,
    )

    if not results:
        print("\nNenhum lote chegou ao horário nesta rodada.")
        return

    for batch_number, status in results:
        print(f"Lote {batch_number}: {status}")

    if any(status == "error" for _, status in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()