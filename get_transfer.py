import sys

import starkbank

from app.stark_client import get_project


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python get_transfer.py TRANSFER_ID")

    transfer_id = sys.argv[1]
    project = get_project()

    transfer = starkbank.transfer.get(transfer_id, user=project)

    print(f"Transfer ID: {transfer.id}")
    print(f"Status: {transfer.status}")
    print(f"Valor em centavos: {transfer.amount}")
    print(f"Tarifa em centavos: {transfer.fee}")
    print(f"External ID: {transfer.external_id}")
    print(f"Transações: {transfer.transaction_ids}")

    print("\nHistórico:")

    logs = starkbank.transfer.log.query(
        transfer_ids=[transfer_id],
        user=project,
    )

    for log in logs:
        print(f"Data: {log.created} | Tipo: {log.type}")
        print(f"Erros: {log.errors}")


if __name__ == "__main__":
    main()