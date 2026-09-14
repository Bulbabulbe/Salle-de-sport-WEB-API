# Salle de sport API

## Sujet fil rouge
Sujet n° 3 - Salle de sport

## Stack
Langage : Python   /   Framework HTTP : Flask   /   Client HTTP : curl

## Lancer le projet

Rien ne tourne encore (le code arrive en séance 2) — voici comment préparer l'environnement et la base de données.

1. Installer Python 3.12+.
2. Créer et activer un environnement virtuel :
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # Linux/Mac
   ```
3. Installer Flask :
   ```bash
   pip install flask
   ```
4. Régénérer la base `gym.db` à partir des fichiers fournis (`schema.sql` + `seed.sql`) :
   ```bash
   python -c "import sqlite3, pathlib; conn = sqlite3.connect('gym.db'); conn.executescript(pathlib.Path('schema.sql').read_text()); conn.executescript(pathlib.Path('seed.sql').read_text()); conn.commit()"
   ```
   (le module `sqlite3` fait partie de la bibliothèque standard de Python, rien d'autre à installer)
