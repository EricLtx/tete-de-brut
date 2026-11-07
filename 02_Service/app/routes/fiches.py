"""Fiche de vérification, décision et export (rempli par S08)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.modeles import DemandeDecision, DemandeFiche, Fiche, ModificationFiche
from app.routes import erreurs, non_implemente

routeur = APIRouter(tags=["fiches"])


@routeur.post(
    "/fiches",
    response_model=Fiche,
    status_code=201,
    summary="Créer la fiche de vérification d'une comparaison",
    responses=erreurs(401, 404, 422, 501),
)
async def creer_fiche(demande: DemandeFiche) -> Fiche:
    """Fiche `fiche.v1` construite par le gabarit : versions à trancher, constat vide, aucune décision."""
    raise non_implemente("POST /v1/fiches")


@routeur.get(
    "/fiches/{id}",
    response_model=Fiche,
    summary="Une fiche de vérification",
    responses=erreurs(404, 422, 501),
)
async def lire_fiche(id: str) -> Fiche:
    """Fiche `fiche.v1` avec son journal de gestes."""
    raise non_implemente("GET /v1/fiches/{id}")


@routeur.patch(
    "/fiches/{id}",
    response_model=Fiche,
    summary="Trancher les versions et écrire le constat",
    responses=erreurs(401, 404, 422, 501),
)
async def modifier_fiche(id: str, modification: ModificationFiche) -> Fiche:
    """Le journaliste tranche chaque version (confirmée, écartée) et écrit le constat ; rien n'est filtré."""
    raise non_implemente("PATCH /v1/fiches/{id}")


@routeur.post(
    "/fiches/{id}/decision",
    response_model=Fiche,
    summary="Enregistrer la décision : à vérifier, ne pas amplifier, prêt à traiter",
    responses=erreurs(401, 404, 422, 501),
)
async def decider(id: str, demande: DemandeDecision) -> Fiche:
    """Décision `decision.v1` prise par une personne ; l'heure est posée par le service."""
    raise non_implemente("POST /v1/fiches/{id}/decision")


@routeur.get(
    "/fiches/{id}/export",
    response_class=HTMLResponse,
    summary="Exporter la fiche en page HTML lisible",
    responses={
        200: {"description": "Page HTML d'une page, constat en tête.", "content": {"text/html": {}}},
        **erreurs(404, 409, 422, 501, route_html=True),
    },
)
async def exporter_fiche(id: str) -> HTMLResponse:
    """Refusé (409) tant que la décision, une version tranchée ou le constat manque."""
    raise non_implemente("GET /v1/fiches/{id}/export")
