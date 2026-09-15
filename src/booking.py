from datetime import datetime, timedelta, timezone

from .db import fetch_one
from .errors import ConflictError, NotFoundError, ValidationError


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _week_bounds(dt: datetime):
    monday = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday, monday + timedelta(days=7)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_reservation(conn, creneau_id: int, adherent_id: int) -> dict:
    """Reserve un creneau pour un adherent, ou le bascule en liste d'attente si complet.

    Toute la verification + l'ecriture se fait dans UNE transaction SQLite serialisee
    (BEGIN IMMEDIATE) pour eviter la course : deux requetes concurrentes sur le meme
    creneau ne peuvent jamais toutes les deux lire "il reste une place".
    """
    conn.execute("BEGIN IMMEDIATE")

    creneau = fetch_one(conn, "creneaux", creneau_id)
    if creneau is None:
        raise NotFoundError("creneau", creneau_id)

    if fetch_one(conn, "adherents", adherent_id) is None:
        raise ValidationError([{"field": "adherent_id", "message": "adherent introuvable"}])

    cours = fetch_one(conn, "cours", creneau["cours_id"])

    debut = _parse(creneau["debut"])
    now = datetime.now(timezone.utc)
    if debut < now:
        raise ConflictError("Ce créneau est déjà passé.", type_slug="creneau-passe", title="Créneau passé")

    jour = creneau["debut"][:10]
    if not (cours["periode_debut"] <= jour <= cours["periode_fin"]):
        raise ConflictError(
            "Ce créneau est hors de la fenêtre d'ouverture du cours.",
            type_slug="hors-fenetre",
            title="Hors fenêtre d'ouverture",
        )

    deja = conn.execute(
        "SELECT id FROM reservations WHERE creneau_id = ? AND adherent_id = ? AND statut = 'confirmee'",
        (creneau_id, adherent_id),
    ).fetchone()
    if deja is not None:
        raise ConflictError(
            "Cet adhérent a déjà une réservation confirmée sur ce créneau.",
            type_slug="deja-reserve",
            title="Réservation déjà existante",
        )

    abonnement = conn.execute(
        "SELECT * FROM abonnements WHERE adherent_id = ? AND debut <= ? AND fin >= ? ORDER BY fin DESC LIMIT 1",
        (adherent_id, jour, jour),
    ).fetchone()
    if abonnement is None:
        raise ValidationError(
            [{"field": "adherent_id", "message": "aucun abonnement actif pour la période de ce créneau"}]
        )

    week_start, week_end = _week_bounds(debut)
    reservations_semaine = conn.execute(
        """
        SELECT COUNT(*) FROM reservations
        JOIN creneaux ON creneaux.id = reservations.creneau_id
        WHERE reservations.adherent_id = ? AND reservations.statut = 'confirmee'
          AND creneaux.debut >= ? AND creneaux.debut < ?
        """,
        (adherent_id, _fmt(week_start), _fmt(week_end)),
    ).fetchone()[0]
    if reservations_semaine >= abonnement["quota_hebdo"]:
        raise ConflictError(
            "Quota hebdomadaire de réservations atteint pour cet abonnement.",
            type_slug="quota-atteint",
            title="Quota atteint",
        )

    cree_le = _fmt(now)

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

    rang = (
        (
            conn.execute(
                "SELECT COALESCE(MAX(rang), 0) FROM listes_attente WHERE creneau_id = ?", (creneau_id,)
            ).fetchone()[0]
        )
        + 1
    )
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
