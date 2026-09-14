import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parent.parent / "gym.db"

app = FastAPI()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class Cours(BaseModel):
    type: str
    coach_id: int
    capacite: int
    jour_semaine: int
    heure_debut: str
    duree_min: int
    periode_debut: str
    periode_fin: str
    fuseau: str


class CoursPatch(BaseModel):
    type: Optional[str] = None
    coach_id: Optional[int] = None
    capacite: Optional[int] = None
    jour_semaine: Optional[int] = None
    heure_debut: Optional[str] = None
    duree_min: Optional[int] = None
    periode_debut: Optional[str] = None
    periode_fin: Optional[str] = None
    fuseau: Optional[str] = None


class Creneau(BaseModel):
    cours_id: int
    debut: str
    fin: str
    places_prises: int = 0


class CreneauPatch(BaseModel):
    cours_id: Optional[int] = None
    debut: Optional[str] = None
    fin: Optional[str] = None
    places_prises: Optional[int] = None


COURS_FIELDS = list(Cours.model_fields.keys())
CRENEAU_FIELDS = list(Creneau.model_fields.keys())


def fetch_one(conn, table: str, id: int):
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


@app.post("/cours", status_code=201)
def create_cours(body: Cours, response: Response):
    conn = get_conn()
    cur = conn.execute(
        f"INSERT INTO cours ({', '.join(COURS_FIELDS)}) VALUES ({', '.join('?' * len(COURS_FIELDS))})",
        [getattr(body, f) for f in COURS_FIELDS],
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    response.headers["Location"] = f"/cours/{new_id}"
    return {"id": new_id, **body.model_dump()}


@app.get("/cours")
def list_cours():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM cours").fetchall()]
    conn.close()
    return rows


@app.get("/cours/{id}")
def get_cours(id: int):
    conn = get_conn()
    row = fetch_one(conn, "cours", id)
    conn.close()
    if row is None:
        raise HTTPException(404)
    return row


@app.put("/cours/{id}")
def replace_cours(id: int, body: Cours):
    conn = get_conn()
    if fetch_one(conn, "cours", id) is None:
        conn.close()
        raise HTTPException(404)
    conn.execute(
        f"UPDATE cours SET {', '.join(f + ' = ?' for f in COURS_FIELDS)} WHERE id = ?",
        [getattr(body, f) for f in COURS_FIELDS] + [id],
    )
    conn.commit()
    row = fetch_one(conn, "cours", id)
    conn.close()
    return row


@app.patch("/cours/{id}")
def update_cours(id: int, body: CoursPatch):
    conn = get_conn()
    if fetch_one(conn, "cours", id) is None:
        conn.close()
        raise HTTPException(404)
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        conn.execute(
            f"UPDATE cours SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
            list(fields.values()) + [id],
        )
        conn.commit()
    row = fetch_one(conn, "cours", id)
    conn.close()
    return row


@app.delete("/cours/{id}", status_code=204)
def delete_cours(id: int):
    conn = get_conn()
    if fetch_one(conn, "cours", id) is None:
        conn.close()
        raise HTTPException(404)
    conn.execute("DELETE FROM cours WHERE id = ?", (id,))
    conn.commit()
    conn.close()


@app.post("/creneaux", status_code=201)
def create_creneau(body: Creneau, response: Response):
    conn = get_conn()
    cur = conn.execute(
        f"INSERT INTO creneaux ({', '.join(CRENEAU_FIELDS)}) VALUES ({', '.join('?' * len(CRENEAU_FIELDS))})",
        [getattr(body, f) for f in CRENEAU_FIELDS],
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    response.headers["Location"] = f"/creneaux/{new_id}"
    return {"id": new_id, **body.model_dump()}


@app.get("/creneaux")
def list_creneaux():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM creneaux").fetchall()]
    conn.close()
    return rows


@app.get("/creneaux/{id}")
def get_creneau(id: int):
    conn = get_conn()
    row = fetch_one(conn, "creneaux", id)
    conn.close()
    if row is None:
        raise HTTPException(404)
    return row


@app.put("/creneaux/{id}")
def replace_creneau(id: int, body: Creneau):
    conn = get_conn()
    if fetch_one(conn, "creneaux", id) is None:
        conn.close()
        raise HTTPException(404)
    conn.execute(
        f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in CRENEAU_FIELDS)} WHERE id = ?",
        [getattr(body, f) for f in CRENEAU_FIELDS] + [id],
    )
    conn.commit()
    row = fetch_one(conn, "creneaux", id)
    conn.close()
    return row


@app.patch("/creneaux/{id}")
def update_creneau(id: int, body: CreneauPatch):
    conn = get_conn()
    if fetch_one(conn, "creneaux", id) is None:
        conn.close()
        raise HTTPException(404)
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        conn.execute(
            f"UPDATE creneaux SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
            list(fields.values()) + [id],
        )
        conn.commit()
    row = fetch_one(conn, "creneaux", id)
    conn.close()
    return row


@app.delete("/creneaux/{id}", status_code=204)
def delete_creneau(id: int):
    conn = get_conn()
    if fetch_one(conn, "creneaux", id) is None:
        conn.close()
        raise HTTPException(404)
    conn.execute("DELETE FROM creneaux WHERE id = ?", (id,))
    conn.commit()
    conn.close()
