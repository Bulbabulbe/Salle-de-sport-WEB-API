# Salle de sport API

## Sujet fil rouge
Sujet n° 3 - Salle de sport

## Stack
Langage : Python   /   Framework HTTP : FastAPI   /   Client HTTP : curl

## Lancer le projet

1. Installer Python 3.12+.
2. Créer et activer un environnement virtuel :
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # Linux/Mac
   ```
3. Installer FastAPI et Uvicorn (serveur ASGI) :
   ```bash
   pip install fastapi uvicorn
   ```
4. Lancer l'API (utilise `gym.db`, déjà présente à la racine) :
   ```bash
   uvicorn src.main:app --reload
   ```
