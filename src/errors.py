from sqlite3 import IntegrityError

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

BASE_ERROR_URL = "https://salle-de-sport-api.local/errors"


class ApiError(Exception):
    status_code = 500
    type_slug = "internal"
    title = "Erreur interne"

    def __init__(self, detail=None, errors=None):
        self.detail = detail
        self.errors = errors
        super().__init__(detail or self.title)


class NotFoundError(ApiError):
    status_code = 404
    type_slug = "not-found"
    title = "Ressource introuvable"

    def __init__(self, resource: str, id):
        super().__init__(detail=f"{resource} {id} n'existe pas.")


class ValidationError(ApiError):
    status_code = 422
    type_slug = "validation"
    title = "Requête invalide"

    def __init__(self, errors: list):
        super().__init__(errors=errors)


class ConflictError(ApiError):
    status_code = 409

    def __init__(self, detail: str, type_slug: str = "conflict", title: str = "Conflit"):
        self.type_slug = type_slug
        self.title = title
        super().__init__(detail=detail)


def _problem(status, type_slug, title, request, detail=None, errors=None):
    body = {
        "type": f"{BASE_ERROR_URL}/{type_slug}",
        "title": title,
        "status": status,
        "instance": str(request.url.path),
    }
    if detail is not None:
        body["detail"] = detail
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type="application/problem+json")


def _field_errors(errs):
    return [
        {
            "field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query")) or "_",
            "message": e["msg"].removeprefix("Value error, "),
        }
        for e in errs
    ]


def register_error_handlers(app):
    @app.exception_handler(ApiError)
    def handle_api_error(request: Request, exc: ApiError):
        return _problem(exc.status_code, exc.type_slug, exc.title, request, detail=exc.detail, errors=exc.errors)

    @app.exception_handler(RequestValidationError)
    def handle_request_validation(request: Request, exc: RequestValidationError):
        errs = exc.errors()
        if len(errs) == 1 and errs[0].get("type") == "json_invalid":
            return _problem(
                400,
                "malformed-body",
                "Corps de requête illisible",
                request,
                detail="Le corps de la requête n'est pas un JSON valide.",
            )
        return _problem(422, "validation", "Requête invalide", request, errors=_field_errors(errs))

    # Levée quand une route valide elle-même un modèle (ex : PATCH qui revalide l'objet fusionné) :
    # même réponse 422 qu'un corps de requête invalide.
    @app.exception_handler(PydanticValidationError)
    def handle_model_validation(request: Request, exc: PydanticValidationError):
        return _problem(422, "validation", "Requête invalide", request, errors=_field_errors(exc.errors()))

    @app.exception_handler(IntegrityError)
    def handle_integrity_error(request: Request, exc: IntegrityError):
        return _problem(409, "conflict", "Conflit d'intégrité", request, detail=str(exc))

    @app.exception_handler(Exception)
    def handle_unexpected(request: Request, exc: Exception):
        return _problem(500, "internal", "Erreur interne", request)
