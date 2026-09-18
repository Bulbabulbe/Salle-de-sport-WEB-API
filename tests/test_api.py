import pytest

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


# --- Creneaux : timestamps UTC stricts (B2) ---


def test_create_creneau_with_utc_timestamps_returns_201(client):
    r = client.post("/creneaux", json={"cours_id": 2, "debut": "2026-11-02T10:00:00Z", "fin": "2026-11-02T11:00:00Z"})
    assert r.status_code == 201
    assert r.json()["places_prises"] == 0


@pytest.mark.parametrize("debut", ["2026-11-02T10:00:00", "2026-11-02"])
def test_create_creneau_without_utc_z_returns_422(client, debut):
    r = client.post("/creneaux", json={"cours_id": 2, "debut": debut, "fin": "2026-11-02T11:00:00Z"})
    assert r.status_code == 422
    assert "debut" in {e["field"] for e in r.json()["errors"]}


# --- Creneaux : places_prises est gere par le serveur (B5) ---


def test_client_cannot_set_places_prises(client):
    r = client.patch("/creneaux/2", json={"places_prises": 999})
    assert r.status_code == 422
    assert client.get("/creneaux/2").json()["places_prises"] == 1


def test_put_creneau_keeps_places_prises(client):
    avant = client.get("/creneaux/3").json()["places_prises"]
    r = client.put("/creneaux/3", json={"cours_id": 7, "debut": "2026-10-05T16:00:00Z", "fin": "2026-10-05T17:30:00Z"})
    assert r.status_code == 200
    assert r.json()["places_prises"] == avant


# --- Pagination : bornes (B6) ---


@pytest.mark.parametrize("url", ["/creneaux?page=0", "/creneaux?limit=0", "/creneaux?limit=-1"])
def test_pagination_out_of_bounds_returns_422(client, url):
    assert client.get(url).status_code == 422


# --- PATCH : l'objet complet reste coherent (B8) ---


def test_patch_cours_periode_fin_before_stored_debut_returns_422(client):
    r = client.patch("/cours/2", json={"periode_fin": "2020-01-01"})
    assert r.status_code == 422


def test_patch_creneau_fin_before_stored_debut_returns_422(client):
    r = client.patch("/creneaux/2", json={"fin": "2020-01-01T00:00:00Z"})
    assert r.status_code == 422
