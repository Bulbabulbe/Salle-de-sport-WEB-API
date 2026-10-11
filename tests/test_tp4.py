"""TP4 : le piège du sujet (réservations concurrentes) et les requêtes conditionnelles."""

import threading
from datetime import datetime, timezone

from src import booking


def test_derniere_place_une_confirmee_une_en_attente(client):
    """Scénario du sujet : le créneau 16 a 1 place restante (9/10) ; deux adhérents
    différents la demandent en même temps."""
    resultats = []

    def reserver(adherent_id):
        r = client.post("/creneaux/16/reservations", json={"adherent_id": adherent_id})
        resultats.append(r.json()["kind"])

    threads = [threading.Thread(target=reserver, args=(a,)) for a in (3, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(resultats) == ["liste_attente", "reservation"]


def test_meme_adherent_deux_fois_en_parallele(client):
    """Même adhérent, même créneau, deux requêtes simultanées : une seule passe."""
    codes = []

    def reserver():
        codes.append(client.post("/creneaux/4/reservations", json={"adherent_id": 6}).status_code)

    threads = [threading.Thread(target=reserver) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(codes) == [201, 409]


def test_deuxieme_inscription_en_liste_attente_refusee(client):
    """Le créneau 5 est complet : première demande en liste d'attente, seconde refusée."""
    r1 = client.post("/creneaux/5/reservations", json={"adherent_id": 3})
    assert r1.status_code == 201
    assert r1.json()["kind"] == "liste_attente"

    r2 = client.post("/creneaux/5/reservations", json={"adherent_id": 3})
    assert r2.status_code == 409
    assert r2.json()["type"].endswith("/deja-inscrit")


def test_creneau_passe_refuse(client, monkeypatch):
    """On avance l'horloge après le créneau 4 : il est désormais passé."""
    monkeypatch.setattr(booking, "utc_now", lambda: datetime(2026, 12, 1, tzinfo=timezone.utc))
    r = client.post("/creneaux/4/reservations", json={"adherent_id": 6})
    assert r.status_code == 409
    assert r.json()["type"].endswith("/creneau-passe")


def test_etag_identique_renvoie_304(client):
    r1 = client.get("/creneaux/2")
    etag = r1.headers["etag"]
    r2 = client.get("/creneaux/2", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_if_match_perime_renvoie_412(client):
    r = client.patch(
        "/creneaux/2",
        json={"fin": "2026-10-05T11:30:00Z"},
        headers={"If-Match": '"etag-perime-0000"'},
    )
    assert r.status_code == 412
    assert r.headers["content-type"] == "application/problem+json"
