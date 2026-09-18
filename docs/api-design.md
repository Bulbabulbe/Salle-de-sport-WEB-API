# Design de l'API - Salle de sport

## (a) Ressources et collections

Modèle du domaine (tables de `gym.db`) :

- **adherents** (id, nom, email) -> souscrit des `abonnements`, fait des `reservations`
- **abonnements** (id, adherent_id, formule, debut, fin, quota_hebdo) -> appartient à un `adherent`
- **coachs** (id, nom, email) -> anime des `cours`
- **cours** (id, type, coach_id, capacite, jour_semaine, heure_debut, duree_min, periode_debut, periode_fin, fuseau) -> a des `creneaux`
- **creneaux** (id, cours_id, debut, fin, places_prises) -> occurrence d'un `cours`, cible des `reservations`
- **reservations** (id, creneau_id, adherent_id, statut, cree_le) -> lie `creneaux` et `adherents`
- **listes_attente** (id, creneau_id, adherent_id, rang, cree_le) -> file d'attente d'un `creneau`

Ressources exposées par l'API à ce stade : `cours` et `creneaux`. Les tables `coachs` et `cours` servent aussi aux vérifications d'existence lors des écritures. Les réservations sont conçues ci-dessous mais pas encore implémentées.

## (b) Opérations

| Opération | Méthode + URI | Succès | Erreurs prévues | Implémentée |
|---|---|---|---|---|
| Lister les cours | `GET /cours` | `200` | - | oui |
| Créer un cours | `POST /cours` | `201` + `Location` | `400`, `422` | oui |
| Lire un cours | `GET /cours/{id}` | `200` | `404` | oui |
| Remplacer un cours | `PUT /cours/{id}` | `200` | `404`, `422` | oui |
| Modifier un cours | `PATCH /cours/{id}` | `200` | `404`, `422` | oui |
| Supprimer un cours | `DELETE /cours/{id}` | `204` | `404`, `409` | oui |
| Lister les créneaux | `GET /creneaux?page&limit&cours&coach&jour&tri&ordre` | `200` | `422` | oui |
| Créer un créneau | `POST /creneaux` | `201` + `Location` | `400`, `422` | oui |
| Lire un créneau | `GET /creneaux/{id}` | `200` | `404` | oui |
| Remplacer / modifier un créneau | `PUT` / `PATCH /creneaux/{id}` | `200` | `404`, `422` | oui |
| Supprimer un créneau | `DELETE /creneaux/{id}` | `204` | `404`, `409` | oui |
| Réserver un créneau | `POST /creneaux/{id}/reservations` | `201` + `Location` | `404`, `409`, `422` | non (séance 4) |
| Lister les réservations | `GET /reservations` | `200` | - | non (séance 4) |
| Rejoindre la liste d'attente | `POST /creneaux/{id}/listes-attente` | `201` + `Location` | `404`, `409` | non (séance 4) |

## (c) Choix de conception

- `reservations` est conçue comme une collection de premier niveau (`GET /reservations`) et non comme une sous-ressource, car une réservation relie deux parents légitimes : un créneau et un adhérent.
- Réserver s'écrira `POST /creneaux/{id}/reservations` : on crée une réservation *sur* un créneau précis, sans mettre de verbe dans l'URI.
- `places_prises` est un compteur géré par le serveur : il est renvoyé en lecture mais absent des modèles d'écriture (`Creneau`, `CreneauPatch`), pour qu'aucun client ne puisse contourner la capacité.
- `creneaux` dépend conceptuellement de `cours` (occurrence de sa règle de récurrence), mais est exposé en collection de premier niveau pour être paginé et filtré sur plusieurs cours à la fois.

## Modèle de données (esquisse)

- `adherents` — 1
- `abonnements` — N-1 vers `adherents`
- `coachs` — 1
- `cours` — N-1 vers `coachs`
- `creneaux` — N-1 vers `cours`
- `reservations` — N-1 vers `creneaux`, N-1 vers `adherents` (table de liaison, mais ressource à part entière car elle porte un état et un historique)
- `listes_attente` — N-1 vers `creneaux`, N-1 vers `adherents`

Stocké vs calculé :
- `places_prises` est stocké (compteur des réservations confirmées).
- « places restantes » n'a pas de colonne : `capacite - places_prises`.
- « complet » n'est pas stocké : `places_prises >= capacite`.

## Conventions de format

Les dates et timestamps sont comparés comme des chaînes (tri, filtres) : un format unique est donc imposé à l'écriture.

- Timestamps des créneaux (`debut`, `fin`) : `AAAA-MM-JJTHH:MM:SSZ` (UTC). Tout autre format est refusé en `422`.
- Dates de période (`periode_debut`, `periode_fin`) : `AAAA-MM-JJ`.
- Heure de début d'un cours (`heure_debut`) : `HH:MM`.

## Format d'erreur

Toutes les erreurs sortent en `application/problem+json` (RFC 9457), produites par un handler central (`src/errors.py`) :

- `400` : corps JSON illisible.
- `404` : ressource de l'URL introuvable.
- `409` : conflit d'intégrité (supprimer une ligne encore référencée).
- `422` : corps lisible mais invalide — champ manquant, mauvais type, valeur hors règle, champ inconnu (rejeté), id référencé inexistant, paramètre de pagination hors bornes, ou `PATCH` qui rendrait l'objet incohérent. Tous les champs fautifs sont renvoyés d'un coup dans `errors[]`.
