import sys

import starkbank

from app.stark_client import get_project


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python list_invoice_events.py INVOICE_ID")

    invoice_id = sys.argv[1]
    project = get_project()

    events = starkbank.event.query(
        after="2026-09-24",
        user=project,
    )

    found = False

    for event in events:
        if event.subscription != "invoice":
            continue

        if event.log.invoice.id != invoice_id:
            continue

        found = True

        print(
            f"Evento: {event.id} | "
            f"Tipo: {event.log.type} | "
            f"Entregue: {event.is_delivered}"
        )

    if not found:
        print("Nenhum evento encontrado para essa Invoice no período.")


if __name__ == "__main__":
    main()