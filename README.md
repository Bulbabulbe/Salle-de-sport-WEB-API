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
4. Lancer l'API (utilise `gym.db`, déjà présente à la racine) :
   ```bash
   uvicorn src.main:app --reload
   ```

## Requêtes (Insomnia)

`requests/insomnia-export.json` : à importer dans Insomnia (`Application > Preferences > Data > Import Data > From File`, ou glisser le fichier). Contient une requête par opération CRUD sur `cours` et `creneaux`, plus `creneaux-list-filtered` pour la collection navigable.

## Pagination

- `GET /creneaux` : offset (`?page=&limit=`).
- `GET /reservations` (historique) : **curseur** (`?limit=&after=`), trié `cree_le,id` décroissant (plus récentes d'abord). `after` encode en base64 la position du dernier élément lu — insensible aux insertions pendant la pagination, contrairement à l'offset (voir `docs/api-design.md`, section "Stratégie face au piège de concurrence").

## Concurrence

`POST /creneaux/{id}/reservations` gère le piège du sujet (double réservation, dépassement de capacité, quota hebdomadaire) — voir `docs/api-design.md`. Réponse `{"kind": "reservation" | "liste_attente", ...}` selon que la place était disponible ou non.

## Cache conditionnel

`GET/PUT/PATCH /creneaux/{id}` supportent `ETag` + `If-None-Match` (→ `304`) + `If-Match` (→ `412` si périmé).

## Tests

```bash
pytest
```
10 tests d'intégration HTTP : 5 du TP3 (2 nominaux + 3 erreurs : 404, 422 multi-champs, 400) + 5 du TP4 (double réservation concurrente, dernière place concurrente, `304`, `412`, pagination curseur stable face à une insertion). Les tests de concurrence lancent 2 requêtes en parallèle (threads) sur la même ressource. Chaque test tourne sur une copie temporaire de `gym.db`, jamais sur la base réelle.

## Erreurs (`application/problem+json`)

Toutes les erreurs passent par un handler central (`src/problem.py`) et sortent au format RFC 9457 — jamais de texte brut ni de stack trace.

- `404` : ressource introuvable (`NotFoundError`).
- `422` : corps lisible mais invalide — champ manquant/mauvais type/hors bornes, **ou** id référencé inexistant (ex: `coach_id` qui n'existe pas), **ou** champ inconnu envoyé (choix : rejeté, pas ignoré). Tous les champs fautifs sont renvoyés d'un coup dans `errors[]`.
- `400` : corps JSON illisible (syntaxe invalide).
- `409` : conflit d'intégrité base de données (ex: suppression d'un cours qui a encore des créneaux).
