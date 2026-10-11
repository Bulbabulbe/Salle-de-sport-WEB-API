# Salle de sport API

## Sujet fil rouge
Sujet n° 3 - Salle de sport

## Stack
Langage : Python   /   Framework HTTP : FastAPI   /   Client HTTP : Insomnia

## Lancer le projet

1. Installer Python 3.12+.
2. Créer et activer un environnement virtuel :
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # Linux/Mac
   ```
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Créer le fichier de secrets à partir de l'exemple fourni (il n'est pas dans le dépôt) :
   ```bash
   cp .env.example .env        # Windows : copy .env.example .env
   ```
   Puis remplir les trois valeurs, par exemple :
   ```text
   TOKEN_COACH=coach-token-de-demo
   TOKEN_ADHERENT=adherent-token-de-demo
   ADHERENT_ID=6
   ```
5. Lancer l'API depuis la racine du projet (elle utilise `gym.db`, déjà présente) :
   ```bash
   python -m uvicorn src.main:app --reload --env-file .env
   ```
   - API : `http://127.0.0.1:8000`
   - Documentation générée : `http://127.0.0.1:8000/docs` (bouton **Authorize** pour coller un token)

## Organisation du code

| Fichier | Rôle |
|---|---|
| `src/main.py` | Routes FastAPI |
| `src/models.py` | Modèles Pydantic et règles de validation |
| `src/errors.py` | Exceptions typées et handler d'erreur central |
| `src/booking.py` | Règles de réservation (fenêtre, doublon, quota, capacité, liste d'attente) |
| `src/auth.py` | Identification par token et règle de rôle |
| `src/db.py` | Connexion SQLite |
| `scripts/export_openapi.py` | Génère `openapi.yaml` depuis l'application |

## Routes

Toutes les routes demandent un token (`Authorization: Bearer <token>`).

| Méthode | URI | Rôle requis |
|---|---|---|
| `GET` | `/cours`, `/cours/{id}` | tout utilisateur authentifié |
| `POST` `PUT` `PATCH` `DELETE` | `/cours`, `/cours/{id}` | coach |
| `GET` | `/creneaux`, `/creneaux/{id}` | tout utilisateur authentifié |
| `POST` `PUT` `PATCH` `DELETE` | `/creneaux`, `/creneaux/{id}` | coach |
| `POST` | `/creneaux/{id}/reservations` | coach, ou adhérent pour lui-même |
| `GET` | `/reservations/{id}`, `/listes-attente/{id}` | tout utilisateur authentifié |

## Conventions de données

- Timestamps des créneaux (`debut`, `fin`) : ISO 8601 en UTC avec `Z`, par exemple `2026-11-02T10:00:00Z`. Tout autre format est refusé (`422`).
- Dates (`periode_debut`, `periode_fin`) : `YYYY-MM-DD`.
- `places_prises` est géré par le serveur : il apparaît dans les réponses mais ne peut pas être envoyé par le client.

## Pagination

`GET /creneaux` : pagination par offset (`?page=&limit=`), `page >= 1`, `limit` entre 1 et 100, filtres `cours`, `coach`, `jour`, tri stable (`?tri=debut,id&ordre=asc`). Réponse : `{"data": [...], "pagination": {...}, "links": {...}}`.

## Réservation et concurrence

`POST /creneaux/{id}/reservations` vérifie et écrit dans une seule transaction verrouillée (`BEGIN IMMEDIATE`) : deux réservations simultanées sur la dernière place donnent une réservation confirmée et une inscription en liste d'attente, jamais deux confirmées. Détails et justification dans `docs/api-design.md`.

### Préparer la démonstration

Les créneaux du jeu de données sont datés d'octobre 2026 ; une fois cette date passée, l'API les refuse (règle « créneau déjà passé »). Avant la démo, créer un créneau futur à une seule place :

```bash
python -m scripts.preparer_demo
```

Il crée le créneau `9001`, daté dans un mois. Les requêtes `tp4-*` de la collection Insomnia pointent dessus :

1. `tp4-reservation-confirmee` (adhérent 3) → `201`, `"kind": "reservation"`
2. `tp4-reservation-liste-attente` (adhérent 6) → `201`, `"kind": "liste_attente"` (la place est prise)
3. `tp4-reservation-409-deja-inscrit` (adhérent 3 à nouveau) → `409`

Relancer le script remet la démo à zéro.

## Cache conditionnel

`GET /creneaux/{id}` renvoie un `ETag`. `If-None-Match` avec l'ETag courant → `304`. `If-Match` avec un ETag périmé sur `PUT`/`PATCH` → `412`.

## Spécification OpenAPI

`openapi.yaml` (OpenAPI 3.1) est généré depuis l'application :

```bash
python -m scripts.export_openapi
```

La documentation s'ouvre sur `http://127.0.0.1:8000/docs`.

## Requêtes (Insomnia)

`requests/insomnia-export.json` : à importer dans Insomnia (`Application > Preferences > Data > Import Data > From File`). 24 requêtes : CRUD, collection filtrée, réservation (confirmée, liste d'attente, `409`), `ETag` (`304`, `412`), erreurs (`400`, `404`, `409`, `422`) et sécurité (`401`, `403`). Les tokens sont dans l'environnement « Base » de la collection.

## Tests

```bash
python -m pytest
```

`python -m` ajoute le dossier courant au chemin d'import, ce qui permet aux tests d'importer `src`.

30 tests d'intégration HTTP :

| Fichier | Contenu |
|---|---|
| `tests/test_api.py` | CRUD, `404`, `422` multi-champs, `400`, formats, `places_prises`, bornes de pagination, cohérence des `PATCH` |
| `tests/test_tp4.py` | Réservations concurrentes, liste d'attente, quota, créneau passé, `304`, `412` |
| `tests/test_tp5.py` | Spec valide, spec fidèle au code, réponse conforme au schéma |
| `tests/test_tp6.py` | `401` sans token, `403` de rôle, `403` de propriété |

Chaque test travaille sur une copie temporaire de `gym.db` et avec une date figée au 2026-10-01, pour donner le même résultat quel que soit le jour d'exécution.

## Erreurs (`application/problem+json`)

Toutes les erreurs passent par le handler central de `src/errors.py` et sortent au format RFC 9457, sans stack trace.

| Code | Quand |
|---|---|
| `400` | corps JSON illisible |
| `401` | token absent ou inconnu |
| `403` | rôle insuffisant, ou réservation pour quelqu'un d'autre |
| `404` | ressource de l'URL introuvable |
| `409` | conflit avec l'état actuel : déjà inscrit, quota atteint, créneau passé, hors période, ou suppression d'une ligne encore référencée |
| `412` | `If-Match` périmé |
| `422` | corps lisible mais invalide : champ manquant, mauvais type, valeur hors règle, champ inconnu, id référencé inexistant, paramètre de pagination hors bornes, ou `PATCH` rendant l'objet incohérent. Tous les champs fautifs sont renvoyés d'un coup dans `errors[]`. |
