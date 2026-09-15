import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

HEURE_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _positive(v):
    if v <= 0:
        raise ValueError("doit être strictement positif")
    return v


def _non_negative(v):
    if v < 0:
        raise ValueError("doit être positif ou nul")
    return v


def _jour_semaine(v):
    if not 1 <= v <= 7:
        raise ValueError("doit être entre 1 (lundi) et 7 (dimanche)")
    return v


def _heure(v):
    if not HEURE_RE.match(v):
        raise ValueError("format attendu HH:MM")
    return v


def _iso_date(v):
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError("format attendu YYYY-MM-DD")
    return v


def _iso_timestamp(v):
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("format attendu ISO 8601 (ex: 2026-10-05T07:00:00Z)")
    return v


class Cours(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    coach_id: int
    capacite: int
    jour_semaine: int
    heure_debut: str
    duree_min: int
    periode_debut: str
    periode_fin: str
    fuseau: str

    _v_jour = field_validator("jour_semaine")(_jour_semaine)
    _v_positifs = field_validator("capacite", "duree_min")(_positive)
    _v_heure = field_validator("heure_debut")(_heure)
    _v_dates = field_validator("periode_debut", "periode_fin")(_iso_date)

    @model_validator(mode="after")
    def check_periode(self):
        if self.periode_fin < self.periode_debut:
            raise ValueError("periode_fin doit être >= periode_debut")
        return self


class CoursPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    coach_id: int | None = None
    capacite: int | None = None
    jour_semaine: int | None = None
    heure_debut: str | None = None
    duree_min: int | None = None
    periode_debut: str | None = None
    periode_fin: str | None = None
    fuseau: str | None = None

    _v_jour = field_validator("jour_semaine")(_jour_semaine)
    _v_positifs = field_validator("capacite", "duree_min")(_positive)
    _v_heure = field_validator("heure_debut")(_heure)
    _v_dates = field_validator("periode_debut", "periode_fin")(_iso_date)

    @model_validator(mode="after")
    def check_periode(self):
        if self.periode_debut is not None and self.periode_fin is not None and self.periode_fin < self.periode_debut:
            raise ValueError("periode_fin doit être >= periode_debut")
        return self


COURS_FIELDS = list(Cours.model_fields.keys())


class Creneau(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cours_id: int
    debut: str
    fin: str
    places_prises: int = 0

    _v_ts = field_validator("debut", "fin")(_iso_timestamp)
    _v_nonneg = field_validator("places_prises")(_non_negative)

    @model_validator(mode="after")
    def check_order(self):
        if self.fin <= self.debut:
            raise ValueError("fin doit être après debut")
        return self


class CreneauPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cours_id: int | None = None
    debut: str | None = None
    fin: str | None = None
    places_prises: int | None = None

    _v_ts = field_validator("debut", "fin")(_iso_timestamp)
    _v_nonneg = field_validator("places_prises")(_non_negative)

    @model_validator(mode="after")
    def check_order(self):
        if self.debut is not None and self.fin is not None and self.fin <= self.debut:
            raise ValueError("fin doit être après debut")
        return self


CRENEAU_FIELDS = list(Creneau.model_fields.keys())


class ReservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adherent_id: int
