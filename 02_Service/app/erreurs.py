"""Enveloppe d'erreur unique : aucune réponse d'erreur du service ne sort sans elle."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ErreurHttp

from app.oriane import CreditsEpuises, OrianeInjoignable, RequeteInvalide

CODES_PAR_STATUT = {
    404: ("introuvable", "Ressource introuvable."),
    405: ("methode_non_permise", "Méthode non permise sur cette route."),
    501: ("non_implemente", "Route prévue au contrat, pas encore implémentée."),
}


class ErreurApi(Exception):
    """Erreur applicative : code `snake_case`, phrase lisible, statut HTTP."""

    def __init__(self, code: str, detail: str, statut: int = 400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.statut = statut


def mode_courant(request: Request) -> str:
    """Mode effectif du service (`direct` ou `enregistre`) lu sur l'application."""
    config = getattr(request.app.state, "config", None)
    return config.mode if config is not None else "enregistre"


def reponse_erreur(code: str, detail: str, statut: int, mode: str) -> JSONResponse:
    """Construit la réponse d'erreur à l'enveloppe `{erreur, detail, mode}`."""
    return JSONResponse(status_code=statut, content={"erreur": code, "detail": detail, "mode": mode})


async def _gerer_erreur_api(request: Request, exc: ErreurApi) -> JSONResponse:
    return reponse_erreur(exc.code, exc.detail, exc.statut, mode_courant(request))


async def _gerer_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Seuls l'emplacement et le message sont repris : jamais la valeur reçue.
    problemes = [
        f"{'.'.join(str(p) for p in e.get('loc', ()))} : {e.get('msg', 'valeur invalide')}"
        for e in exc.errors()
    ]
    detail = "Requête invalide. " + " ; ".join(problemes) if problemes else "Requête invalide."
    return reponse_erreur("validation", detail, 422, mode_courant(request))


async def _gerer_http(request: Request, exc: ErreurHttp) -> JSONResponse:
    code, detail = CODES_PAR_STATUT.get(exc.status_code, ("erreur_http", "La requête n'a pas pu aboutir."))
    return reponse_erreur(code, detail, exc.status_code, mode_courant(request))


async def _gerer_oriane_injoignable(request: Request, exc: OrianeInjoignable) -> JSONResponse:
    return reponse_erreur("oriane_injoignable", exc.raison, 503, mode_courant(request))


async def _gerer_credits_epuises(request: Request, exc: CreditsEpuises) -> JSONResponse:
    return reponse_erreur("credits_epuises", exc.raison, 503, mode_courant(request))


async def _gerer_requete_invalide(request: Request, exc: RequeteInvalide) -> JSONResponse:
    return reponse_erreur("validation", exc.raison, 422, mode_courant(request))


async def _gerer_inattendue(request: Request, exc: Exception) -> JSONResponse:
    return reponse_erreur("erreur_interne", "Erreur interne du service.", 500, mode_courant(request))


def installer_gestionnaires(app: FastAPI) -> None:
    """Enregistre les gestionnaires qui ramènent toute erreur à l'enveloppe."""
    app.add_exception_handler(ErreurApi, _gerer_erreur_api)
    app.add_exception_handler(RequestValidationError, _gerer_validation)
    app.add_exception_handler(ErreurHttp, _gerer_http)
    app.add_exception_handler(OrianeInjoignable, _gerer_oriane_injoignable)
    app.add_exception_handler(CreditsEpuises, _gerer_credits_epuises)
    app.add_exception_handler(RequeteInvalide, _gerer_requete_invalide)
    app.add_exception_handler(Exception, _gerer_inattendue)
