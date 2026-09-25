import os 
from pathlib import Path

import starkbank

def get_project() -> starkbank.Project:
    project_id = os.environ.get("STARKBANK_PROJECT_ID", "").strip()

    if not project_id:
        raise ValueError("Configure STARKBANK_PROJECT_ID.")

    project_root = Path(__file__).resolve().parent.parent
    private_key_path = project_root / ".keys" / "private-key.pem"

    if not private_key_path.is_file():
        raise RuntimeError("Chave privada não encontrada em .keys/private-key.pem.")
    
    return starkbank.Project(
        environment="sandbox",
        id=project_id,
        private_key=private_key_path.read_text(encoding="utf-8")
    )

