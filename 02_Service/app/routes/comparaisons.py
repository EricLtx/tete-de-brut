"""Comparaison de deux versions au mot (rempli par S07)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modeles import DemandeComparaison, Ecart
from app.routes import erreurs, non_implemente

routeur = APIRouter(tags=["comparaisons"])


@routeur.post(
    "/comparaisons",
    response_model=Ecart,
    summary="Comparer une reprise à sa source (idempotent)",
    responses=erreurs(401, 404, 422, 501),
)
async def creer_comparaison(demande: DemandeComparaison) -> Ecart:
    """Identifiant dérivé du couple (source, reprise) : une seconde demande rend la même ressource, en 200."""
    raise non_implemente("POST /v1/comparaisons")


@routeur.get(
    "/comparaisons/{id}",
    response_model=Ecart,
    summary="Une comparaison : opérations au mot, écarts de légende et de texte à l'écran",
    responses=erreurs(404, 422, 501),
)
async def lire_comparaison(id: str) -> Ecart:
    """Écart `ecart.v1` : opérations retire, ajoute, remplace avec positions, jamais un verdict."""
    raise non_implemente("GET /v1/comparaisons/{id}")
