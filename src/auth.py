import os

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import ForbiddenError, UnauthorizedError

# Les tokens ne sont pas dans le code : ils sont lus dans l'environnement (fichier .env,
# ignoré par git ; voir .env.example). Sans eux, aucune requête n'est authentifiée.

# auto_error=False : c'est notre handler qui renvoie le 401 en problem+json.
# Déclarer le schéma ici le fait apparaître dans la spec OpenAPI et dans la doc générée.
bearer = HTTPBearer(auto_error=False, description="Token de démo fourni dans .env")


def utilisateur_courant(identifiants: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """Identifie l'appelant à partir de l'en-tête Authorization: Bearer <token>."""
    token = identifiants.credentials.strip() if identifiants else ""
    token_coach = os.environ.get("TOKEN_COACH", "")
    token_adherent = os.environ.get("TOKEN_ADHERENT", "")

    if token and token == token_coach:
        return {"role": "coach", "adherent_id": None}
    if token and token == token_adherent:
        return {"role": "adherent", "adherent_id": int(os.environ.get("ADHERENT_ID", "0"))}
    raise UnauthorizedError()


def exiger_coach(utilisateur: dict):
    """Les cours et les créneaux ne sont gérés que par un coach."""
    if utilisateur["role"] != "coach":
        raise ForbiddenError("Seul un coach peut modifier les cours et les créneaux.")
