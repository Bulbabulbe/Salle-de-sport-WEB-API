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

Ressources exposées par l'API : `cours`, `creneaux`, `reservations` et `listes-attente`. Les tables `adherents`, `abonnements` et `coachs` servent aux vérifications (id existant, abonnement actif, quota) mais n'ont pas de route.

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
| Lire un créneau | `GET /creneaux/{id}` | `200` + `ETag`, ou `304` | `401`, `404` | oui |
| Remplacer / modifier un créneau | `PUT` / `PATCH /creneaux/{id}` | `200` + `ETag` | `401`, `403`, `404`, `412`, `422` | oui |
| Supprimer un créneau | `DELETE /creneaux/{id}` | `204` | `404`, `409` | oui |
| Réserver un créneau | `POST /creneaux/{id}/reservations` | `201` + `Location` | `401`, `403`, `404`, `409`, `422` | oui |
| Lire une réservation | `GET /reservations/{id}` | `200` | `401`, `404` | oui |
| Lire une inscription en liste d'attente | `GET /listes-attente/{id}` | `200` | `401`, `404` | oui |

## (c) Choix de conception

- `reservations` est conçue comme une collection de premier niveau (`GET /reservations`) et non comme une sous-ressource, car une réservation relie deux parents légitimes : un créneau et un adhérent.
- Réserver s'écrit `POST /creneaux/{id}/reservations` : on crée une réservation *sur* un créneau précis, sans mettre de verbe dans l'URI. Si le créneau est complet, la même requête inscrit en liste d'attente (`201`, `"kind": "liste_attente"`) : ce n'est pas une erreur, c'est la règle métier.
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

## Stratégie face au piège de concurrence

### Le piège
Plannings récurrents, fenêtre de réservation, quota hebdomadaire par adhérent et capacité limitée par créneau : toutes ces contraintes doivent tenir en même temps, y compris quand deux requêtes arrivent au même instant. Sans protection, deux requêtes peuvent lire le même état (« il reste une place ») avant que l'une n'écrive : deux réservations confirmées au-delà de la capacité, ou un même adhérent inscrit deux fois.

### Ce que fait l'API
- Toute la logique de `POST /creneaux/{id}/reservations` (`src/booking.py`) s'exécute dans **une transaction verrouillée dès son début** (`BEGIN IMMEDIATE`) : la seconde requête attend que la première ait écrit avant de lire l'état à son tour.
- Deux réservations concurrentes sur la dernière place → une confirmée, l'autre en liste d'attente (`201`, `"kind": "liste_attente"`), jamais deux confirmées.
- Adhérent déjà réservé **ou** déjà en liste d'attente sur ce créneau → `409` (`deja-inscrit`).
- Quota hebdomadaire atteint, compté sur la semaine du créneau visé → `409` (`quota-atteint`). Créneau passé → `409` (`creneau-passe`) ; hors période du cours → `409` (`hors-fenetre`).
- `GET/PUT/PATCH /creneaux/{id}` : `ETag` + `If-None-Match` (`304`) et `If-Match` (`412` si l'ETag fourni est périmé), pour ne pas écraser la modification d'un autre client.

### Pourquoi REST ici
`ETag` et `If-Match` réutilisent un mécanisme HTTP standard, compris par tout client, plutôt qu'un verrou applicatif maison. Les codes `409` et `412` portent le sens du conflit dans le protocole lui-même : le client sait s'il doit renoncer, recharger ou réessayer, sans avoir à interpréter un format d'erreur propriétaire. Et comme chaque requête est indépendante, deux clients peuvent taper sur la même ressource sans session partagée côté serveur.

### Conséquences
Le client doit lire `kind` dans la réponse : un `201` ne veut pas toujours dire « confirmé ». Pour être protégé contre l'écrasement, il doit renvoyer l'`ETag` reçu en `If-Match` ; sans ce header, l'écriture passe sans contrôle. Non géré aujourd'hui : l'annulation d'une réservation et la promotion automatique du premier de la liste d'attente.

## Sécurité

- Toutes les routes exigent un token : `Authorization: Bearer <token>`. Sans token ou avec un token inconnu → `401` (`non-authentifie`).
- Deux rôles de démonstration : `coach` et `adherent`. Les tokens sont lus dans l'environnement (`.env`, ignoré par git ; `.env.example` est fourni), jamais écrits dans le code.
- Règle de rôle : créer, modifier ou supprimer un cours ou un créneau est réservé au coach → `403` (`droits-insuffisants`) sinon.
- Règle de propriété : un adhérent ne peut réserver que pour lui-même → `403` s'il envoie l'`adherent_id` de quelqu'un d'autre.

## Spécification OpenAPI

`openapi.yaml` (OpenAPI 3.1) est **généré depuis l'application** par `python -m scripts.export_openapi` : la spec ne peut donc pas diverger du code. Les erreurs y sont déclarées en `application/problem+json`, et le schéma de sécurité `HTTPBearer` y figure. La documentation se consulte sur `/docs` quand l'API tourne. Trois tests (`tests/test_tp5.py`) vérifient que la spec est valide, qu'elle correspond au code, et qu'une réponse réelle respecte le schéma déclaré.
