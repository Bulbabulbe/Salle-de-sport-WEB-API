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
4. Lancer l'API depuis la racine du projet (elle utilise `gym.db`, déjà présente à la racine) :
   ```bash
   python -m uvicorn src.main:app --reload
   ```
   L'API écoute sur `http://127.0.0.1:8000`.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `src/main.py` | Routes FastAPI |
| `src/models.py` | Modèles Pydantic et règles de validation |
| `src/errors.py` | Exceptions typées et handler d'erreur central |
| `src/db.py` | Connexion SQLite |

## Routes

| Méthode | URI | Rôle |
|---|---|---|
| `GET` `POST` | `/cours` | Lister / créer un cours |
| `GET` `PUT` `PATCH` `DELETE` | `/cours/{id}` | Lire / remplacer / modifier / supprimer un cours |
| `GET` `POST` | `/creneaux` | Lister (paginé, filtrable, triable) / créer un créneau |
| `GET` `PUT` `PATCH` `DELETE` | `/creneaux/{id}` | Idem pour un créneau |

## Conventions de données

- Timestamps des créneaux (`debut`, `fin`) : ISO 8601 en UTC avec `Z`, par exemple `2026-11-02T10:00:00Z`. Tout autre format est refusé (`422`).
- Dates (`periode_debut`, `periode_fin`) : `YYYY-MM-DD`.
- `places_prises` est géré par le serveur : il apparaît dans les réponses mais ne peut pas être envoyé par le client.

## Requêtes (Insomnia)

`requests/insomnia-export.json` : à importer dans Insomnia (`Application > Preferences > Data > Import Data > From File`). Contient une requête par opération CRUD sur `cours` et `creneaux`, la collection filtrée, et les cas d'erreur (`400`, `404`, `409`, `422`).

## Pagination

`GET /creneaux` : pagination par offset (`?page=&limit=`), avec `page >= 1` et `limit` entre 1 et 100. Réponse sous la forme `{"data": [...], "pagination": {...}, "links": {...}}`. La pagination par curseur sera ajoutée en séance 4.

## Tests

```bash
python -m pytest
```

`python -m` ajoute le dossier courant au chemin d'import, ce qui permet aux tests d'importer le package `src`.

15 tests d'intégration HTTP (`tests/test_api.py`) : cas nominaux CRUD, `404`, `422` multi-champs, `400`, format des timestamps, protection de `places_prises`, bornes de pagination, cohérence des `PATCH`. Chaque test travaille sur une copie temporaire de `gym.db`, jamais sur la base réelle.

## Erreurs (`application/problem+json`)

Toutes les erreurs passent par le handler central de `src/errors.py` et sortent au format RFC 9457, sans stack trace.

- `400` : corps JSON illisible.
- `404` : ressource de l'URL introuvable.
- `409` : conflit d'intégrité (ex : supprimer un cours qui a encore des créneaux).
- `422` : corps lisible mais invalide — champ manquant, mauvais type, valeur hors règle, champ inconnu (rejeté, pas ignoré), id référencé inexistant, paramètre de pagination hors bornes, ou `PATCH` qui rendrait l'objet incohérent. Tous les champs fautifs sont renvoyés d'un coup dans `errors[]`.
