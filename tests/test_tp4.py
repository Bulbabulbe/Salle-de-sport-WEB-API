import sqlite3
import threading


def test_double_booking_same_adherent_gives_one_201_and_one_409(client):
    """Meme adherent, meme creneau, deux requetes en parallele -> un seul gagnant."""
    results = []

    def book():
        r = client.post("/creneaux/4/reservations", json={"adherent_id": 6})
        results.append(r.status_code)

    threads = [threading.Thread(target=book) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == [201, 409]


def test_last_spot_gives_one_confirmed_and_one_waitlisted(client):
    """Creneau 16 a exactement 1 place restante (9/10) ; deux adherents differents
    la visent en parallele -> une reservation confirmee, l'autre en liste d'attente,
    jamais deux confirmees (pas de depassement de capacite)."""
    results = []

    def book(adherent_id):
        r = client.post("/creneaux/16/reservations", json={"adherent_id": adherent_id})
        results.append(r.json()["kind"])

    threads = [threading.Thread(target=book, args=(a,)) for a in (3, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["liste_attente", "reservation"]


def test_etag_if_none_match_returns_304(client):
    r1 = client.get("/creneaux/2")
    etag = r1.headers["etag"]
    r2 = client.get("/creneaux/2", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_etag_if_match_stale_returns_412(client):
    r = client.patch(
        "/creneaux/2",
        json={"places_prises": 5},
        headers={"If-Match": '"stale-etag-0000"'},
    )
    assert r.status_code == 412
    assert r.headers["content-type"] == "application/problem+json"


def test_cursor_pagination_no_duplicate_or_skip_on_insert(client, test_db_path):
    """Lire la page 1, inserer directement un element qui se placerait DANS la page 1
    (meme cree_le que la limite de page, id plus grand -> passerait devant en tri
    DESC), puis lire la page suivante par le curseur : ni doublon, ni saut."""
    limit = 3
    r1 = client.get(f"/reservations?limit={limit}")
    page1_ids = {row["id"] for row in r1.json()["data"]}
    boundary_cree_le = r1.json()["data"][-1]["cree_le"]
    next_link = r1.json()["links"]["next"]

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO reservations (id, creneau_id, adherent_id, statut, cree_le) VALUES (999999, 4, 6, 'confirmee', ?)",
        (boundary_cree_le,),
    )
    conn.commit()
    conn.close()

    r2 = client.get(next_link)
    page2_ids = {row["id"] for row in r2.json()["data"]}

    assert page1_ids.isdisjoint(page2_ids)
    assert 999999 not in page2_ids
