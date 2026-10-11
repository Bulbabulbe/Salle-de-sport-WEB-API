import hashlib
import json
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Header, Query, Response

from .auth import exiger_coach, utilisateur_courant
from .booking import create_reservation
from .db import db, fetch_one
from .errors import ForbiddenError, NotFoundError, PreconditionFailedError, ValidationError, register_error_handlers
from .models import COURS_FIELDS, CRENEAU_FIELDS, Cours, CoursOut, CoursPatch, Creneau, CreneauPatch, ReservationIn

# Toutes les routes exigent un token (sauf la doc : /docs et /openapi.json).
app = FastAPI(
    title="Salle de sport API",
    version="1.0.0",
    dependencies=[Depends(utilisateur_courant)],
)
register_error_handlers(app)

CRENEAU_SORT_KEYS = {"id", "debut", "fin", "cours_id", "places_prises"}

# Réponses d'erreur déclarées dans la spec OpenAPI : toutes au format problem+json.
PROBLEM = {"content": {"application/problem+json": {}}}
ERREURS_LECTURE = {401: PROBLEM, 404: PROBLEM}
ERREURS_ECRITURE = {400: PROBLEM, 401: PROBLEM, 403: PROBLEM, 404: PROBLEM, 409: PROBLEM, 422: PROBLEM}


def etag_de(row: dict) -> str:
    """Empreinte de la version actuelle de la ressource."""
    return '"' + hashlib.sha1(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16] + '"'


def require_exists(conn, table: str, id: int | None, field: str):
    if id is not None and fetch_one(conn, table, id) is None:
        raise ValidationError([{"field": field, "message": f"{table} introuvable"}])


@app.post("/cours", status_code=201, responses=ERREURS_ECRITURE)
def create_cours(body: Cours, response: Response, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        require_exists(conn, "coachs", body.coach_id, "coach_id")
        cur = conn.execute(
            f"INSERT INTO cours ({', '.join(COURS_FIELDS)}) VALUES ({', '.join('?' * len(COURS_FIELDS))})",
            [getattr(body, f) for f in COURS_FIELDS],
        )
        conn.commit()
        new_id = cur.lastrowid
    response.headers["Location"] = f"/cours/{new_id}"
    return {"id": new_id, **body.model_dump()}


@app.get("/cours", responses=ERREURS_LECTURE)
def list_cours():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cours").fetchall()]


@app.get("/cours/{id}", response_model=CoursOut, responses=ERREURS_LECTURE)
def get_cours(id: int):
    with db() as conn:
        row = fetch_one(conn, "cours", id)
    if row is None:
        raise NotFoundError("cours", id)
    return row


@app.put("/cours/{id}", responses=ERREURS_ECRITURE)
def replace_cours(id: int, body: Cours, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        if fetch_one(conn, "cours", id) is None:
            raise NotFoundError("cours", id)
        require_exists(conn, "coachs", body.coach_id, "coach_id")
        conn.execute(
            f"UPDATE cours SET {', '.join(f + ' = ?' for f in COURS_FIELDS)} WHERE id = ?",
            [getattr(body, f) for f in COURS_FIELDS] + [id],
        )
        conn.commit()
        return fetch_one(conn, "cours", id)


@app.patch("/cours/{id}", responses=ERREURS_ECRITURE)
def update_cours(id: int, body: CoursPatch, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        current = fetch_one(conn, "cours", id)
        if current is None:
            raise NotFoundError("cours", id)
        require_exists(conn, "coachs", body.coach_id, "coach_id")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        # On revalide l'objet complet (valeurs actuelles + champs reçus) : sinon un PATCH de
        # periode_fin seule pourrait la placer avant la periode_debut déjà enregistrée.
        cours_modifie = {f: current[f] for f in COURS_FIELDS}
        cours_modifie.update(fields)
        Cours(**cours_modifie)
        if fields:
            conn.execute(
                f"UPDATE cours SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                list(fields.values()) + [id],
            )
            conn.commit()
        return fetch_one(conn, "cours", id)


@app.delete("/cours/{id}", status_code=204, responses=ERREURS_ECRITURE)
def delete_cours(id: int, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        if fetch_one(conn, "cours", id) is None:
            raise NotFoundError("cours", id)
        conn.execute("DELETE FROM cours WHERE id = ?", (id,))
        conn.commit()


@app.post("/creneaux", status_code=201, responses=ERREURS_ECRITURE)
def create_creneau(body: Creneau, response: Response, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        require_exists(conn, "cours", body.cours_id, "cours_id")
        cur = conn.execute(
            f"INSERT INTO creneaux ({', '.join(CRENEAU_FIELDS)}) VALUES ({', '.join('?' * len(CRENEAU_FIELDS))})",
            [getattr(body, f) for f in CRENEAU_FIELDS],
        )
        conn.commit()
        new_id = cur.lastrowid
        row = fetch_one(conn, "creneaux", new_id)
    response.headers["Location"] = f"/creneaux/{new_id}"
    return row


@app.get("/creneaux", responses=ERREURS_LECTURE)
def list_creneaux(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    cours: str | None = None,
    coach: str | None = None,
    jour: int | None = None,
    tri: str = "debut,id",
    ordre: str = "asc",
):
    conditions = []
    params: list = []
    if cours is not None:
        conditions.append("cours.type = ?")
        params.append(cours)
    if coach is not None:
        conditions.append("coachs.nom = ?")
        params.append(coach)
    if jour is not None:
        conditions.append("cours.jour_semaine = ?")
        params.append(jour)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    from_clause = (
        f"FROM creneaux JOIN cours ON cours.id = creneaux.cours_id JOIN coachs ON coachs.id = cours.coach_id {where}"
    )

    sort_keys = [k.strip() for k in tri.split(",") if k.strip() in CRENEAU_SORT_KEYS]
    if not sort_keys:
        sort_keys = ["debut", "id"]
    direction = "DESC" if ordre == "desc" else "ASC"
    order_by = ", ".join(f"creneaux.{k} {direction}" for k in sort_keys)

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) {from_clause}", params).fetchone()[0]
        offset = (page - 1) * limit
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT creneaux.* {from_clause} ORDER BY {order_by} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        ]

    def link(target_page: int) -> str:
        qs = {"page": target_page, "limit": limit, "tri": tri, "ordre": ordre}
        if cours is not None:
            qs["cours"] = cours
        if coach is not None:
            qs["coach"] = coach
        if jour is not None:
            qs["jour"] = jour
        return f"/creneaux?{urlencode(qs)}"

    return {
        "data": rows,
        "pagination": {"page": page, "limit": limit, "total": total},
        "links": {
            "next": link(page + 1) if page * limit < total else None,
            "prev": link(page - 1) if page > 1 else None,
        },
    }


@app.get("/creneaux/{id}", responses={**ERREURS_LECTURE, 304: {"description": "Non modifie"}})
def get_creneau(id: int, response: Response, if_none_match: str | None = Header(None)):
    with db() as conn:
        row = fetch_one(conn, "creneaux", id)
    if row is None:
        raise NotFoundError("creneau", id)
    etag = etag_de(row)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return row


@app.put("/creneaux/{id}", responses={**ERREURS_ECRITURE, 412: PROBLEM})
def replace_creneau(
    id: int,
    body: Creneau,
    response: Response,
    if_match: str | None = Header(None),
    utilisateur: dict = Depends(utilisateur_courant),
):
    exiger_coach(utilisateur)
    with db() as conn:
        current = fetch_one(conn, "creneaux", id)
        if current is None:
            raise NotFoundError("creneau", id)
        if if_match is not None and if_match != etag_de(current):
            raise PreconditionFailedError()
        require_exists(conn, "cours", body.cours_id, "cours_id")
        conn.execute(
            f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in CRENEAU_FIELDS)} WHERE id = ?",
            [getattr(body, f) for f in CRENEAU_FIELDS] + [id],
        )
        conn.commit()
        row = fetch_one(conn, "creneaux", id)
    response.headers["ETag"] = etag_de(row)
    return row


@app.patch("/creneaux/{id}", responses={**ERREURS_ECRITURE, 412: PROBLEM})
def update_creneau(
    id: int,
    body: CreneauPatch,
    response: Response,
    if_match: str | None = Header(None),
    utilisateur: dict = Depends(utilisateur_courant),
):
    exiger_coach(utilisateur)
    with db() as conn:
        current = fetch_one(conn, "creneaux", id)
        if current is None:
            raise NotFoundError("creneau", id)
        if if_match is not None and if_match != etag_de(current):
            raise PreconditionFailedError()
        require_exists(conn, "cours", body.cours_id, "cours_id")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        # Même principe que pour les cours : un PATCH de fin seule ne doit pas la placer avant debut.
        creneau_modifie = {f: current[f] for f in CRENEAU_FIELDS}
        creneau_modifie.update(fields)
        Creneau(**creneau_modifie)
        if fields:
            conn.execute(
                f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                list(fields.values()) + [id],
            )
            conn.commit()
        row = fetch_one(conn, "creneaux", id)
    response.headers["ETag"] = etag_de(row)
    return row


@app.delete("/creneaux/{id}", status_code=204, responses=ERREURS_ECRITURE)
def delete_creneau(id: int, utilisateur: dict = Depends(utilisateur_courant)):
    exiger_coach(utilisateur)
    with db() as conn:
        if fetch_one(conn, "creneaux", id) is None:
            raise NotFoundError("creneau", id)
        conn.execute("DELETE FROM creneaux WHERE id = ?", (id,))
        conn.commit()


@app.post("/creneaux/{id}/reservations", status_code=201, responses=ERREURS_ECRITURE)
def reserver_creneau(
    id: int,
    body: ReservationIn,
    response: Response,
    utilisateur: dict = Depends(utilisateur_courant),
):
    # Regle metier : un adherent ne reserve que pour lui-meme ; un coach peut inscrire n'importe qui.
    if utilisateur["role"] == "adherent" and body.adherent_id != utilisateur["adherent_id"]:
        raise ForbiddenError("Un adherent ne peut reserver que pour lui-meme.")
    with db() as conn:
        resultat = create_reservation(conn, id, body.adherent_id)
    cible = "reservations" if resultat["kind"] == "reservation" else "listes-attente"
    response.headers["Location"] = f"/{cible}/{resultat['id']}"
    return resultat


@app.get("/reservations/{id}", responses=ERREURS_LECTURE)
def get_reservation(id: int):
    with db() as conn:
        row = fetch_one(conn, "reservations", id)
    if row is None:
        raise NotFoundError("reservation", id)
    return row


@app.get("/listes-attente/{id}", responses=ERREURS_LECTURE)
def get_liste_attente(id: int):
    with db() as conn:
        row = fetch_one(conn, "listes_attente", id)
    if row is None:
        raise NotFoundError("liste_attente", id)
    return row
