# TP 1 : modèle de ressources + lancement du projet

**Format** : projet individuel sur votre fil rouge.
**Durée** : 20 min de TP guidé.
**Prérequis** : aucun, c'est la séance d'entrée du module. HTTP de base supposé acquis.
**Langage** : libre. Vous codez dans celui que vous maîtrisez déjà. Ce TP ne demande encore aucun
code : uniquement de la conception et l'initialisation du dépôt.

---

## Objectifs

- Initialiser le dépôt de votre projet fil rouge (structure, `README`, lancement documenté).
- Concevoir le modèle de ressources et le jeu d'URIs de **votre** sujet.
- Choisir votre sujet et l'acter dans le dépôt.

---

## Votre sujet : ressources de départ

Point de départ, à compléter et à affiner dans `docs/api-design.md` :

| Sujet | Ressources clés | Relation structurante |
|---|---|---|
| 1. Bibliothèque | `ouvrages`, `exemplaires`, `adherents`, `emprunts`, `reservations` | `ouvrages/{id}/exemplaires` |
| 2. Cinéma | `films`, `salles`, `seances`, `reservations`, `paiements` | `seances/{id}/reservations` |
| 3. Salle de sport | `adherents`, `abonnements`, `cours`, `creneaux`, `reservations`, `listes_attente` | `cours/{id}/creneaux` |

---

## J1 : initialiser le dépôt (~5 min)

Créez un dépôt avec cette structure de départ (les noms de fichiers de code dépendent de votre
langage) :

```text
mon-api/
  README.md
  docs/
    api-design.md
  src/                  (votre code, à partir de la séance 2)
  requests/             (collection de requêtes, à partir de la séance 2)
```

`README.md` - squelette à compléter au fil des séances :

```markdown
# <Nom de votre API>

## Sujet fil rouge
Sujet n° _ - <nom>   (à remplir en fin de séance 1)

## Stack
Langage : _   /   Framework HTTP : _   /   Client HTTP : _

## Lancer le projet
<commande unique, ou procédure README pas à pas si pas de Docker>
```

**Lancement documenté** : `docker compose up` si Docker vous est familier, sinon une procédure
`README` précise (installer les dépendances, variable(s) d'environnement, commande de démarrage,
URL de base). Docker n'est **pas** exigé.

---

## J2 : `docs/api-design.md` pour votre sujet (~12 min)

Rédigez trois sections.

**(a) Ressources et collections** - au moins **4 ressources liées**. Pour chacune : nom de la
collection (pluriel), 3 à 5 attributs, et ses relations.

```markdown
## Ressources
- ouvrages       (id, titre, auteurs[], isbn, annee)         -> a des exemplaires
- exemplaires    (id, ouvrage_id, etat, localisation)        -> sous-ressource d'ouvrages
- adherents      (id, nom, email, actif)
- emprunts       (id, exemplaire_id, adherent_id, du, au)    -> lie exemplaire et adherent
```

**(b) Tableau URI x verbe x code de statut** pour les opérations principales (au moins 8 lignes) :

| Opération | Méthode + URI | Succès | Erreurs prévues |
|---|---|---|---|
| Lister le catalogue | `GET /ouvrages` | `200` | - |
| Lire un ouvrage | `GET /ouvrages/{id}` | `200` | `404` |
| Créer un ouvrage | `POST /ouvrages` | `201` + `Location` | `400`, `422` |
| Lister les exemplaires | `GET /ouvrages/{id}/exemplaires` | `200` | `404` |
| Emprunter | `POST /exemplaires/{id}/emprunts` | `201` + `Location` | `404`, `409` |
| ... | ... | ... | ... |

**(c) 2 à 3 choix de conception justifiés**, une phrase chacun. Exemples : « `emprunts` est une
collection de premier niveau et non une sous-ressource de `adherents`, car un emprunt se consulte
aussi côté exemplaire » ; « rendre un exemplaire = `PATCH /emprunts/{id}` qui renseigne `rendu_le`, plutôt qu'un
`POST /exemplaires/{id}/retour` (verbe dans l'URI) ou qu'un `DELETE` (l'historique des emprunts
disparaîtrait) ».

Rappels de conception (voir deck) : noms au pluriel, pas de verbe dans l'URI, filtres et
pagination en *query string*, sous-ressource quand la vie de l'une dépend de l'autre.

**Niveau visé** : votre design doit atteindre le **niveau 2** de l'échelle de Richardson
(ressources identifiées par URI **et** verbes et codes HTTP utilisés pour leur sens). Relisez votre
tableau (b) : un `POST` qui sert à lire, ou une erreur renvoyée en `200`, vous fait redescendre au
niveau 1. L'hypermédia (niveau 3) n'est pas demandé ici : vous n'en ajouterez qu'une touche en
séance 2, les liens de pagination.

---

## J3 : acter votre sujet et committer (~3 min)

- Le sujet a été choisi en début de séance, avant J2 (**un étudiant par sujet** ; en cas de
  double préférence, arbitrage formateur).
- Complétez `## Sujet fil rouge` dans le `README`.
- Premier commit :

```bash
git init
git add -A
git commit -m "chore: init du depot, api-design, sujet choisi"
```

---

## Contrats de référence (agnostiques)

```http
POST /ouvrages HTTP/1.1
Content-Type: application/json

{ "titre": "Dune", "auteurs": ["Herbert"], "isbn": "978-2221252055" }
```

```http
HTTP/1.1 201 Created
Location: /ouvrages/128
Content-Type: application/json

{ "id": 128, "titre": "Dune", "auteurs": ["Herbert"], "isbn": "978-2221252055" }
```

| Verbe | Sûr | Idempotent |
|---|---|---|
| `GET` | oui | oui |
| `POST` | non | non |
| `PUT` | non | oui |
| `PATCH` | non | non par défaut |
| `DELETE` | non | oui |

---

## Livrable (commité en fin de séance)

- Dépôt initialisé : `README` (sujet, stack, lancement documenté), arborescence, premier commit.
- `docs/api-design.md` : (a) ressources et collections (au moins 4 ressources liées), (b) tableau
  URI x verbe x code de statut des opérations principales, (c) 2 à 3 choix justifiés.
- Sujet fil rouge **acté** dans le `README`.

## Critères de réussite

- [ ] Le dépôt se clone et le `README` explique comment lancer le projet (même si rien ne tourne
      encore).
- [ ] `api-design.md` liste au moins 4 ressources **liées** entre elles.
- [ ] Chaque opération principale a un code de statut de succès **et** ses erreurs prévues.
- [ ] Aucun verbe dans les URIs, collections au pluriel.
- [ ] Le design est au niveau 2 de Richardson : chaque verbe est employé pour sa sémantique.
- [ ] Sujet choisi, premier commit poussé.

## Travail personnel avant la séance 2

- Relire votre `api-design.md`.
- Installer le framework HTTP de votre langage et un client HTTP de votre choix (suggestions :
  Bruno, Postman, Insomnia, Hoppscotch ou `curl`). Aucun code à écrire.
