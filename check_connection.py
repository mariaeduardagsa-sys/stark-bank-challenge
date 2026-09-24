import os
from pathlib import Path

import starkbank

def main() -> None:
    project_id = os.environ["STARKBANK_PROJECT_ID"]

    project_root = Path(__file__).resolve().parent
    private_key_path = project_root / ".keys" / "private-key.pem"
    private_key = private_key_path.read_text(encoding="utf-8")

    project = starkbank.Project(
        environment="sandbox",
        id=project_id,
        private_key=private_key,
    )

    balance = starkbank.balance.get(user=project)

    print("Conexão com o Sandbox realizada com sucesso!")
    print(f"Saldo atual: {balance.amount}")
    print(f"Moeda: {balance.currency}")

if __name__ == "__main__":
    main()