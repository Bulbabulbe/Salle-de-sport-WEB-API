"""TP5 : la spec OpenAPI est valide, et le code la respecte."""

from pathlib import Path

import jsonschema
import yaml
from openapi_spec_validator import validate

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"
SPEC = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def test_la_spec_est_valide():
    """openapi.yaml respecte la grammaire OpenAPI 3.1 (lève une exception sinon)."""
    assert SPEC["openapi"].startswith("3.1")
    validate(SPEC)


def test_la_spec_correspond_au_code(client):
    """La spec commitée est bien celle que produit l'application d'aujourd'hui."""
    assert SPEC == client.app.openapi(), "spec perimee : relancer python -m scripts.export_openapi"


def test_la_reponse_respecte_le_schema_declare(client):
    """Test de contrat : le corps réel de GET /cours/1 est validé contre le schéma de la spec."""
    schema = SPEC["paths"]["/cours/{id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    schema = {**schema, "components": SPEC["components"]}  # pour résoudre les $ref

    reponse = client.get("/cours/1")
    assert reponse.status_code == 200
    jsonschema.validate(reponse.json(), schema)


def test_les_erreurs_sont_declarees_en_problem_json(client):
    """Le 404 renvoyé est bien celui annoncé par la spec, dans le bon format."""
    declare = SPEC["paths"]["/cours/{id}"]["get"]["responses"]["404"]["content"]
    assert "application/problem+json" in declare

    reponse = client.get("/cours/999999")
    assert reponse.status_code == 404
    assert reponse.headers["content-type"] == "application/problem+json"
