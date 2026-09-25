import starkbank

from app.stark_client import get_project


def main() -> None:
    project = get_project()
    balance = starkbank.balance.get(user=project)

    print("Conexão com o Sandbox realizada com sucesso!")
    print(f"Saldo em centavos: {balance.amount}")
    print(f"Moeda: {balance.currency}")


if __name__ == "__main__":
    main()