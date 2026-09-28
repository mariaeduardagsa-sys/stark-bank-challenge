import starkbank

from app.stark_client import get_project


def main() -> None:
    project = get_project()
    found = 0

    transfers = starkbank.transfer.query(user=project)

    for transfer in transfers:
        found += 1

        print(f"ID: {transfer.id}")
        print(f"Criada em: {transfer.created}")
        print(f"Status: {transfer.status}")
        print(f"Valor em centavos: {transfer.amount}")
        print(f"External ID: {transfer.external_id}")
        print(f"Tags: {transfer.tags}")
        print(f"Transações: {transfer.transaction_ids}")
        print()

    print(f"Operações encontradas: {found}")


if __name__ == "__main__":
    main()
