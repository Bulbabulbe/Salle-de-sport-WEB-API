"""Écrit openapi.yaml à partir de l'application : la spec ne peut pas mentir sur le code.

Usage (depuis la racine) : python -m scripts.export_openapi
"""

from pathlib import Path

import yaml

from src.main import app

CIBLE = Path(__file__).resolve().parent.parent / "openapi.yaml"
CIBLE.write_text(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"spec ecrite : {CIBLE.name}")
