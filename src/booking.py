from datetime import datetime, timedelta, timezone

from .db import fetch_one
from .errors import ConflictError, NotFoundError, ValidationError


# Isolée dans une fonction pour que les tests puissent la remplacer par une heure fixe :
# sinon, ils échoueraient dès que les créneaux du jeu de données seraient passés.
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _semaine(dt: datetime):
    """Lundi 00:00 UTC de la semaine du créneau, et lundi suivant."""
    lundi = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return _fmt(lundi), _fmt(lundi + timedelta(days=7))


def create_reservation(conn, creneau_id: int, adherent_id: int) -> dict:
    """Réserve un créneau, ou inscrit en liste d'attente s'il est complet.

    Les vérifications et l'écriture sont dans UNE transaction verrouillée dès le début
    (BEGIN IMMEDIATE) : deux requêtes concurrentes ne peuvent pas lire toutes les deux
    qu'il reste la dernière place.
    """
    conn.execute("BEGIN IMMEDIATE")

    creneau = fetch_one(conn, "creneaux", creneau_id)
    if creneau is None:
        raise NotFoundError("creneau", creneau_id)
    if fetch_one(conn, "adherents", adherent_id) is None:
        raise ValidationError([{"field": "adherent_id", "message": "adherent introuvable"}])

    cours = fetch_one(conn, "cours", creneau["cours_id"])
    jour = creneau["debut"][:10]

    if _parse(creneau["debut"]) < utc_now():
        raise ConflictError("Ce créneau est déjà passé.", type_slug="creneau-passe", title="Créneau passé")

    if not (cours["periode_debut"] <= jour <= cours["periode_fin"]):
        raise ConflictError(
            "Ce créneau est hors de la période d'ouverture du cours.",
            type_slug="hors-fenetre",
            title="Hors fenêtre d'ouverture",
        )

    deja_reserve = conn.execute(
        "SELECT id FROM reservations WHERE creneau_id = ? AND adherent_id = ? AND statut = 'confirmee'",
        (creneau_id, adherent_id),
    ).fetchone()
    deja_en_attente = conn.execute(
        "SELECT id FROM listes_attente WHERE creneau_id = ? AND adherent_id = ?",
        (creneau_id, adherent_id),
    ).fetchone()
    if deja_reserve is not None or deja_en_attente is not None:
        raise ConflictError(
            "Cet adhérent est déjà inscrit sur ce créneau (réservation ou liste d'attente).",
            type_slug="deja-inscrit",
            title="Adhérent déjà inscrit",
        )

    abonnement = conn.execute(
        "SELECT * FROM abonnements WHERE adherent_id = ? AND debut <= ? AND fin >= ? ORDER BY fin DESC LIMIT 1",
        (adherent_id, jour, jour),
    ).fetchone()
    if abonnement is None:
        raise ValidationError(
            [{"field": "adherent_id", "message": "aucun abonnement actif pour la période de ce créneau"}]
        )

    debut_semaine, fin_semaine = _semaine(_parse(creneau["debut"]))
    deja_cette_semaine = conn.execute(
        """
        SELECT COUNT(*) FROM reservations
        JOIN creneaux ON creneaux.id = reservations.creneau_id
        WHERE reservations.adherent_id = ? AND reservations.statut = 'confirmee'
          AND creneaux.debut >= ? AND creneaux.debut < ?
        """,
        (adherent_id, debut_semaine, fin_semaine),
    ).fetchone()[0]
    if deja_cette_semaine >= abonnement["quota_hebdo"]:
        raise ConflictError(
            "Quota hebdomadaire de réservations atteint pour cet abonnement.",
            type_slug="quota-atteint",
            title="Quota atteint",
        )

    cree_le = _fmt(utc_now())

    if creneau["places_prises"] < cours["capacite"]:
        cur = conn.execute(
            "INSERT INTO reservations (creneau_id, adherent_id, statut, cree_le) VALUES (?, ?, 'confirmee', ?)",
            (creneau_id, adherent_id, cree_le),
        )
        conn.execute("UPDATE creneaux SET places_prises = places_prises + 1 WHERE id = ?", (creneau_id,))
        conn.commit()
        return {
            "kind": "reservation",
            "id": cur.lastrowid,
            "creneau_id": creneau_id,
            "adherent_id": adherent_id,
            "statut": "confirmee",
            "cree_le": cree_le,
        }

    rang = conn.execute(
        "SELECT COALESCE(MAX(rang), 0) + 1 FROM listes_attente WHERE creneau_id = ?", (creneau_id,)
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO listes_attente (creneau_id, adherent_id, rang, cree_le) VALUES (?, ?, ?, ?)",
        (creneau_id, adherent_id, rang, cree_le),
    )
    conn.commit()
    return {
        "kind": "liste_attente",
        "id": cur.lastrowid,
        "creneau_id": creneau_id,
        "adherent_id": adherent_id,
        "rang": rang,
        "cree_le": cree_le,
    }
