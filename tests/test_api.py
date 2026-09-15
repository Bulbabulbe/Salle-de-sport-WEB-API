COURS_VALIDE = {
    "type": "Boxe",
    "coach_id": 1,
    "capacite": 15,
    "jour_semaine": 3,
    "heure_debut": "18:00",
    "duree_min": 60,
    "periode_debut": "2026-09-07",
    "periode_fin": "2026-12-28",
    "fuseau": "Europe/Paris",
}


def test_list_cours_returns_200(client):
    r = client.get("/cours")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_cours_returns_201_and_location(client):
    r = client.post("/cours", json=COURS_VALIDE)
    assert r.status_code == 201
    assert r.headers["location"].startswith("/cours/")


def test_get_cours_not_found_returns_404_problem_json(client):
    r = client.get("/cours/999999")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["status"] == 404
    assert body["type"].endswith("/not-found")


def test_create_cours_invalid_body_returns_422_with_all_field_errors(client):
    body = {**COURS_VALIDE, "capacite": -5, "jour_semaine": 9}
    r = client.post("/cours", json=body)
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
    fields = {e["field"] for e in r.json()["errors"]}
    assert fields == {"capacite", "jour_semaine"}


def test_create_cours_malformed_json_returns_400(client):
    r = client.post(
        "/cours",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.headers["content-type"] == "application/problem+json"
