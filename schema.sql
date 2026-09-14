-- Kit de données - Sujet 3 : salle de sport (SQLite)
-- Point de départ : adaptez-le à votre docs/api-design.md.
PRAGMA foreign_keys = ON;

CREATE TABLE adherents (
  id     INTEGER PRIMARY KEY,
  nom    VARCHAR(100) NOT NULL,
  email  VARCHAR(254) NOT NULL
);

CREATE TABLE abonnements (
  id           INTEGER PRIMARY KEY,
  adherent_id  INTEGER NOT NULL REFERENCES adherents (id),
  formule      VARCHAR(10) NOT NULL CHECK (formule IN ('essentiel', 'premium', 'illimite')),
  debut        DATE NOT NULL,
  fin          DATE NOT NULL,
  quota_hebdo  INTEGER NOT NULL
);

CREATE TABLE coachs (
  id     INTEGER PRIMARY KEY,
  nom    VARCHAR(100) NOT NULL,
  email  VARCHAR(254) NOT NULL
);

-- règle de récurrence : chaque semaine, jour_semaine (1 = lundi ... 7 = dimanche) à heure_debut
-- (heure locale du fuseau), entre periode_debut et periode_fin
CREATE TABLE cours (
  id             INTEGER PRIMARY KEY,
  type           VARCHAR(50) NOT NULL,
  coach_id       INTEGER NOT NULL REFERENCES coachs (id),
  capacite       INTEGER NOT NULL,
  jour_semaine   INTEGER NOT NULL CHECK (jour_semaine BETWEEN 1 AND 7),
  heure_debut    TIME NOT NULL,
  duree_min      INTEGER NOT NULL,
  periode_debut  DATE NOT NULL,
  periode_fin    DATE NOT NULL,
  fuseau         VARCHAR(64) NOT NULL
);

-- occurrences d'un cours ; debut et fin en UTC
CREATE TABLE creneaux (
  id             INTEGER PRIMARY KEY,
  cours_id       INTEGER NOT NULL REFERENCES cours (id),
  debut          TIMESTAMP NOT NULL,
  fin            TIMESTAMP NOT NULL,
  places_prises  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE reservations (
  id           INTEGER PRIMARY KEY,
  creneau_id   INTEGER NOT NULL REFERENCES creneaux (id),
  adherent_id  INTEGER NOT NULL REFERENCES adherents (id),
  statut       VARCHAR(10) NOT NULL CHECK (statut IN ('confirmee', 'annulee')),
  cree_le      TIMESTAMP NOT NULL
);

CREATE TABLE listes_attente (
  id           INTEGER PRIMARY KEY,
  creneau_id   INTEGER NOT NULL REFERENCES creneaux (id),
  adherent_id  INTEGER NOT NULL REFERENCES adherents (id),
  rang         INTEGER NOT NULL,
  cree_le      TIMESTAMP NOT NULL
);
