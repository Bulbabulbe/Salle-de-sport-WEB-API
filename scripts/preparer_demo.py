"""Prépare le créneau de démonstration du scénario concurrent.

Les créneaux du jeu de données sont datés d'octobre 2026 : une fois cette date passée,
l'API les refuse (règle « créneau déjà passé »). Ce script crée un cours et un créneau
de démo, datés dans un mois (hors des semaines déjà remplies par le jeu de données,
pour que le quota hebdomadaire des adhérents soit libre), avec une capacité de 1 place.

Deux réservations simultanées sur ce créneau donnent donc : une confirmée, une en liste
d'attente. Relancer le script remet la démo à zéro.

Usage (depuis la racine) : python -m scripts.preparer_demo
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from src.db import DB_PATH

COURS_ID = 9001
CRENEAU_ID = 9001

jour_demo = (datetime.now(timezone.utc) + timedelta(days=30)).replace(minute=0, second=0, microsecond=0)
debut = jour_demo.strftime("%Y-%m-%dT%H:00:00Z")
fin = (jour_demo + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00Z")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

# Remise à zéro d'une démo précédente
conn.execute("DELETE FROM listes_attente WHERE creneau_id = ?", (CRENEAU_ID,))
conn.execute("DELETE FROM reservations WHERE creneau_id = ?", (CRENEAU_ID,))
conn.execute("DELETE FROM creneaux WHERE id = ?", (CRENEAU_ID,))
conn.execute("DELETE FROM cours WHERE id = ?", (COURS_ID,))

conn.execute(
    """INSERT INTO cours (id, type, coach_id, capacite, jour_semaine, heure_debut, duree_min,
                          periode_debut, periode_fin, fuseau)
       VALUES (?, 'Demo', 1, 1, ?, ?, 60, '2026-01-01', '2030-12-31', 'Europe/Paris')""",
    (COURS_ID, jour_demo.isoweekday(), jour_demo.strftime("%H:00")),
)
conn.execute(
    "INSERT INTO creneaux (id, cours_id, debut, fin, places_prises) VALUES (?, ?, ?, ?, 0)",
    (CRENEAU_ID, COURS_ID, debut, fin),
)
conn.commit()
conn.close()

print(f"Creneau de demo pret : /creneaux/{CRENEAU_ID} ({debut}), 1 place disponible.")
print("Scenario : deux reservations simultanees -> une confirmee, une en liste d'attente.")
