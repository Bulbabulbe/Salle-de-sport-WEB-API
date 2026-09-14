# Design de l'API - Salle de sport

## (a) Ressources et collections

- **adherents** (id, nom, email) -> souscrit des `abonnements`, fait des `reservations`
- **abonnements** (id, adherent_id, formule, debut, fin, quota_hebdo) -> sous-ressource d'`adherents`
- **coachs** (id, nom, email) -> anime des `cours`
- **cours** (id, type, coach_id, capacite, jour_semaine, heure_debut, duree_min) -> a des `creneaux`
- **creneaux** (id, cours_id, debut, fin, places_prises) -> sous-ressource de `cours`, cible des `reservations`
- **reservations** (id, creneau_id, adherent_id, statut, cree_le) -> lie `creneaux` et `adherents`
- **listes_attente** (id, creneau_id, adherent_id, rang, cree_le) -> sous-ressource de `creneaux`

## (b) Opérations principales

| Opération | Méthode + URI | Succès | Erreurs prévues |
|---|---|---|---|
| Lister les cours | `GET /cours` | `200` | - |
| Lire un cours | `GET /cours/{id}` | `200` | `404` |
| Créer un cours | `POST /cours` | `201` + `Location` | `400`, `422` |
| Lister les créneaux d'un cours | `GET /cours/{id}/creneaux` | `200` | `404` |
| Lister les abonnements d'un adhérent | `GET /adherents/{id}/abonnements` | `200` | `404` |
| Créer un abonnement | `POST /adherents/{id}/abonnements` | `201` + `Location` | `400`, `404`, `422` |
| Réserver un créneau | `POST /creneaux/{id}/reservations` | `201` + `Location` | `404`, `409` |
| Annuler une réservation | `PATCH /reservations/{id}` | `200` | `404`, `409` |
| Rejoindre la liste d'attente | `POST /creneaux/{id}/listes-attente` | `201` + `Location` | `404`, `409` |
| Lister les adhérents | `GET /adherents` | `200` | - |

## (c) Choix de conception

- `reservations` est une collection de premier niveau et non une sous-ressource d'`adherents`, car une réservation se consulte aussi côté créneau (`creneaux/{id}/reservations` en filtre).
- Annuler une réservation = `PATCH /reservations/{id}` (passe `statut` à `annulee`), plutôt qu'un `DELETE` (l'historique disparaîtrait) ou un `POST /reservations/{id}/annuler` (verbe dans l'URI).
- `creneaux` est une sous-ressource de `cours` car un créneau n'existe pas sans le cours qui le génère (règle de récurrence), mais reste accessible en `GET /creneaux/{id}` pour les réservations et listes d'attente.

## Modèle de données (esquisse)

- `adherents` (id, nom, email) — 1
- `abonnements` (id, adherent_id, formule, debut, fin, quota_hebdo) — N-1 vers `adherents`
- `coachs` (id, nom, email) — 1
- `cours` (id, type, coach_id, capacite, jour_semaine, heure_debut, duree_min, periode_debut, periode_fin, fuseau) — N-1 vers `coachs`
- `creneaux` (id, cours_id, debut, fin, places_prises) — N-1 vers `cours` (occurrence générée par la règle de récurrence du cours)
- `reservations` (id, creneau_id, adherent_id, statut, cree_le) — N-1 vers `creneaux`, N-1 vers `adherents` (table de liaison, mais reste une ressource car elle porte un état/historique)
- `listes_attente` (id, creneau_id, adherent_id, rang, cree_le) — N-1 vers `creneaux`, N-1 vers `adherents`

Stocké vs calculé :
- `places_prises` est stocké (compteur mis à jour à chaque réservation/annulation).
- "places restantes" n'a pas de colonne : `capacite - places_prises`, calculé à la lecture.
- "complet" (booléen) n'est pas stocké : calculé (`places_prises >= capacite`).
