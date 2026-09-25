import os
from pathlib import Path

import starkbank


def main() -> None:
    project_root = Path(__file__).resolve().parent
    private_key_path = project_root / ".keys" / "private-key.pem"

    project = starkbank.Project(
        environment="sandbox",
        id=os.environ["STARKBANK_PROJECT_ID"],
        private_key=private_key_path.read_text(encoding="utf-8"),
    )

    invoice = starkbank.Invoice(
        amount=1000,
        name="Buzz Aldrin",
        tax_id="012.345.678-90",
        fine=0,
        interest=0,
        tags=["challenge", "manual-test"],
    )

    created_invoices = starkbank.invoice.create(
        [invoice],
        user=project,
    )

    created_invoice = created_invoices[0]

    print(f"Invoice ID: {created_invoice.id}")
    print(f"Status: {created_invoice.status}")
    print(f"Valor em centavos: {created_invoice.amount}")


if __name__ == "__main__":
    main()