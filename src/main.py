from urllib.parse import urlencode

from fastapi import FastAPI, Header, Response

from .booking import create_reservation
from .db import db, fetch_one
from .errors import NotFoundError, PreconditionFailedError, ValidationError, register_error_handlers
from .models import COURS_FIELDS, CRENEAU_FIELDS, Cours, CoursPatch, Creneau, CreneauPatch, ReservationIn
from .utils import compute_etag, decode_cursor, encode_cursor

app = FastAPI()
register_error_handlers(app)

CRENEAU_SORT_KEYS = {"id", "debut", "fin", "cours_id", "places_prises"}


def require_exists(conn, table: str, id: int | None, field: str):
    if id is not None and fetch_one(conn, table, id) is None:
        raise ValidationError([{"field": field, "message": f"{table} introuvable"}])


@app.post("/cours", status_code=201)
def create_cours(body: Cours, response: Response):
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


@app.get("/cours")
def list_cours():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cours").fetchall()]


@app.get("/cours/{id}")
def get_cours(id: int):
    with db() as conn:
        row = fetch_one(conn, "cours", id)
    if row is None:
        raise NotFoundError("cours", id)
    return row


@app.put("/cours/{id}")
def replace_cours(id: int, body: Cours):
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


@app.patch("/cours/{id}")
def update_cours(id: int, body: CoursPatch):
    with db() as conn:
        if fetch_one(conn, "cours", id) is None:
            raise NotFoundError("cours", id)
        require_exists(conn, "coachs", body.coach_id, "coach_id")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if fields:
            conn.execute(
                f"UPDATE cours SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                list(fields.values()) + [id],
            )
            conn.commit()
        return fetch_one(conn, "cours", id)


@app.delete("/cours/{id}", status_code=204)
def delete_cours(id: int):
    with db() as conn:
        if fetch_one(conn, "cours", id) is None:
            raise NotFoundError("cours", id)
        conn.execute("DELETE FROM cours WHERE id = ?", (id,))
        conn.commit()


@app.post("/creneaux", status_code=201)
def create_creneau(body: Creneau, response: Response):
    with db() as conn:
        require_exists(conn, "cours", body.cours_id, "cours_id")
        cur = conn.execute(
            f"INSERT INTO creneaux ({', '.join(CRENEAU_FIELDS)}) VALUES ({', '.join('?' * len(CRENEAU_FIELDS))})",
            [getattr(body, f) for f in CRENEAU_FIELDS],
        )
        conn.commit()
        new_id = cur.lastrowid
    response.headers["Location"] = f"/creneaux/{new_id}"
    return {"id": new_id, **body.model_dump()}


@app.get("/creneaux")
def list_creneaux(
    page: int = 1,
    limit: int = 20,
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


@app.get("/creneaux/{id}")
def get_creneau(id: int, response: Response, if_none_match: str | None = Header(None)):
    with db() as conn:
        row = fetch_one(conn, "creneaux", id)
    if row is None:
        raise NotFoundError("creneau", id)
    etag = compute_etag(row)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return row


@app.put("/creneaux/{id}")
def replace_creneau(id: int, body: Creneau, response: Response, if_match: str | None = Header(None)):
    with db() as conn:
        current = fetch_one(conn, "creneaux", id)
        if current is None:
            raise NotFoundError("creneau", id)
        if if_match is not None and if_match != compute_etag(current):
            raise PreconditionFailedError()
        require_exists(conn, "cours", body.cours_id, "cours_id")
        conn.execute(
            f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in CRENEAU_FIELDS)} WHERE id = ?",
            [getattr(body, f) for f in CRENEAU_FIELDS] + [id],
        )
        conn.commit()
        row = fetch_one(conn, "creneaux", id)
    response.headers["ETag"] = compute_etag(row)
    return row


@app.patch("/creneaux/{id}")
def update_creneau(id: int, body: CreneauPatch, response: Response, if_match: str | None = Header(None)):
    with db() as conn:
        current = fetch_one(conn, "creneaux", id)
        if current is None:
            raise NotFoundError("creneau", id)
        if if_match is not None and if_match != compute_etag(current):
            raise PreconditionFailedError()
        require_exists(conn, "cours", body.cours_id, "cours_id")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if fields:
            conn.execute(
                f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                list(fields.values()) + [id],
            )
            conn.commit()
        row = fetch_one(conn, "creneaux", id)
    response.headers["ETag"] = compute_etag(row)
    return row


@app.delete("/creneaux/{id}", status_code=204)
def delete_creneau(id: int):
    with db() as conn:
        if fetch_one(conn, "creneaux", id) is None:
            raise NotFoundError("creneau", id)
        conn.execute("DELETE FROM creneaux WHERE id = ?", (id,))
        conn.commit()


@app.post("/creneaux/{id}/reservations", status_code=201)
def reserve_creneau(id: int, body: ReservationIn, response: Response):
    with db() as conn:
        result = create_reservation(conn, id, body.adherent_id)
    if result["kind"] == "reservation":
        response.headers["Location"] = f"/reservations/{result['id']}"
    else:
        response.headers["Location"] = f"/listes-attente/{result['id']}"
    return result


@app.get("/reservations")
def list_reservations(limit: int = 20, after: str | None = None):
    params: list = []
    where = ""
    if after is not None:
        cree_le, last_id = decode_cursor(after)
        where = "WHERE (cree_le < ? OR (cree_le = ? AND id < ?))"
        params = [cree_le, cree_le, int(last_id)]

    with db() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM reservations {where} ORDER BY cree_le DESC, id DESC LIMIT ?",
                params + [limit],
            ).fetchall()
        ]

    next_link = None
    if len(rows) == limit:
        last = rows[-1]
        cursor = encode_cursor(last["cree_le"], last["id"])
        next_link = f"/reservations?limit={limit}&after={cursor}"

    return {"data": rows, "links": {"next": next_link}}


@app.get("/reservations/{id}")
def get_reservation(id: int):
    with db() as conn:
        row = fetch_one(conn, "reservations", id)
    if row is None:
        raise NotFoundError("reservation", id)
    return row


@app.get("/listes-attente/{id}")
def get_liste_attente(id: int):
    with db() as conn:
        row = fetch_one(conn, "listes_attente", id)
    if row is None:
        raise NotFoundError("liste_attente", id)
    return row
