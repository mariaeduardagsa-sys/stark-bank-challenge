import argparse
import logging
import time
from pathlib import Path

from app.event_runner import run_pending_events
from app.stark_client import get_project


logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processa continuamente os eventos do Sandbox."
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Autoriza o processamento e a criação de Transfers no Sandbox.",
    )

    args = parser.parse_args()

    if not args.execute:
        parser.error(
            "Use --execute para iniciar. "
            "Para prévia, use python process_pending.py."
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    database_path = (
        Path(__file__).resolve().parent / "data" / "events.db"
    )
    project = get_project()

    logger.info("Processador de eventos iniciado. Use Ctrl+C para parar.")

    try:
        while True:
            results = run_pending_events(database_path, project)

            for event_id, status in results:
                logger.info(
                    "Event %s: %s",
                    event_id,
                    status,
                )

            time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Processador de eventos interrompido.")


if __name__ == "__main__":
    main()