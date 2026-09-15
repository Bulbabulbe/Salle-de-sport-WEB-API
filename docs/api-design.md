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

## Stratégie face au piège de concurrence

### Le piège
Plannings récurrents (un cours génère ses créneaux sur plusieurs semaines) + fenêtre de réservation (un créneau ne se réserve que tant qu'il n'est pas passé et que le cours est dans sa période active) + quota par adhérent (limite hebdomadaire posée par son abonnement) + capacité limitée par créneau : plusieurs contraintes qui doivent toutes tenir en même temps, y compris quand deux requêtes arrivent au même instant sur la même ressource. Concrètement, deux requêtes concurrentes peuvent lire le même état (places restantes, quota déjà consommé) avant que l'une des deux n'écrive — sans protection, deux réservations peuvent toutes les deux "voir" une place libre et confirmer, dépassant la capacité, ou un même adhérent se retrouver avec deux réservations actives sur le même créneau.

### Ce que fait l'API
- Toute la logique de réservation (`POST /creneaux/{id}/reservations`) s'exécute dans **une transaction SQLite explicitement sérialisée** (`BEGIN IMMEDIATE`) : la première requête qui l'atteint verrouille l'écriture, la seconde attend qu'elle commit ou échoue avant de lire l'état à son tour — impossible que les deux lisent le même instantané "il reste une place".
- Un même adhérent qui réserve deux fois le même créneau en parallèle → la deuxième requête trouve la première déjà en base → `409` (`deja-reserve`).
- Quota hebdomadaire dépassé (compté sur la semaine du créneau visé, pas la semaine de la requête) → `409` (`quota-atteint`).
- Créneau déjà complet au moment de la vérification → **pas d'erreur** : bascule automatique en `listes_attente` (rang suivant), réponse `201` avec `Location: /listes-attente/{id}` au lieu de `/reservations/{id}`.
- `GET/PATCH/PUT /creneaux/{id}` supportent `ETag` + `If-None-Match` (lecture, `304`) + `If-Match` (écriture, `412` si l'ETag fourni ne correspond plus à l'état actuel) — protège contre l'écrasement d'une modification concurrente sur le créneau lui-même (ex: deux coachs qui éditent la capacité en même temps).
- `GET /reservations` (historique) est paginé par **curseur** (`cree_le,id` décroissant) plutôt que par offset : un nouvel élément inséré pendant la pagination ne décale pas les positions des pages déjà lues, contrairement à l'offset où un insert peut faire apparaître un doublon ou sauter un élément entre deux pages.

### Pourquoi REST ici
`ETag`/`If-Match` réutilisent un mécanisme HTTP standard (cache conditionnel) plutôt qu'un verrou applicatif maison — outillage et sémantique déjà compris par tout client HTTP. Les codes de statut (`409`, `412`) portent le sens du conflit directement dans le protocole, sans avoir à documenter un format d'erreur métier séparé. Le curseur reste une simple query string, donc un lien cliquable/partageable, pas un état de session côté serveur.

### Conséquences
Le client doit savoir lire `kind` dans la réponse de réservation (`"reservation"` vs `"liste_attente"`) plutôt que de supposer qu'un `201` veut toujours dire "confirmé". Il doit aussi renvoyer l'`ETag` reçu en `If-Match` s'il veut éviter d'écraser une modification concurrente — s'il l'ignore, ses écritures passent toujours (pas de protection par défaut). Ce qu'on ne gère pas : annulation automatique en cas de non-présentation, promotion automatique du premier de la liste d'attente quand une place se libère (aucun code ne le fait aujourd'hui, resterait à ajouter).
