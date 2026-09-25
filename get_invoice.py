import os
import sys
from pathlib import Path

import starkbank


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python get_invoice.py INVOICE_ID")

    invoice_id = sys.argv[1]

    project_root = Path(__file__).resolve().parent
    private_key_path = project_root / ".keys" / "private-key.pem"

    project = starkbank.Project(
        environment="sandbox",
        id=os.environ["STARKBANK_PROJECT_ID"],
        private_key=private_key_path.read_text(encoding="utf-8"),
    )

    invoice = starkbank.invoice.get(invoice_id, user=project)

    print(f"Invoice ID: {invoice.id}")
    print(f"Status: {invoice.status}")
    print(f"Valor em centavos: {invoice.amount}")
    print(f"Tarifa em centavos: {invoice.fee}")
    print(f"IDs das transações: {invoice.transaction_ids}")


if __name__ == "__main__":
    main()