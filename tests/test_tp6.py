"""TP6 : authentification (401) et autorisation métier (403)."""

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


def test_sans_token_renvoie_401(client_sans_token):
    r = client_sans_token.get("/cours")
    assert r.status_code == 401
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["type"].endswith("/non-authentifie")


def test_token_invalide_renvoie_401(api):
    from fastapi.testclient import TestClient

    r = TestClient(api, headers={"Authorization": "Bearer mauvais-token"}).get("/cours")
    assert r.status_code == 401


def test_adherent_ne_peut_pas_creer_un_cours(client_adherent):
    """Règle de rôle : les cours sont gérés par les coachs."""
    r = client_adherent.post("/cours", json=COURS_VALIDE)
    assert r.status_code == 403
    assert r.json()["type"].endswith("/droits-insuffisants")


def test_adherent_ne_peut_pas_reserver_pour_un_autre(client_adherent):
    """Règle de propriété : un adhérent ne réserve que pour lui-même (il a l'id 6)."""
    r = client_adherent.post("/creneaux/4/reservations", json={"adherent_id": 3})
    assert r.status_code == 403

    r_ok = client_adherent.post("/creneaux/4/reservations", json={"adherent_id": 6})
    assert r_ok.status_code == 201


def test_coach_peut_creer_un_cours(client):
    r = client.post("/cours", json=COURS_VALIDE)
    assert r.status_code == 201
