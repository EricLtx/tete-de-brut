"""Comparaison de deux versions au mot (S07)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import base
from app.ecart import TYPE_DOCUMENT, calculer_ecart, identifiant_comparaison
from app.erreurs import ErreurApi, mode_courant
from app.modeles import ECART_V1, DemandeComparaison, Ecart, Video
from app.routes import erreurs

routeur = APIRouter(tags=["comparaisons"])


@routeur.post(
    "/comparaisons",
    response_model=Ecart,
    summary="Comparer une reprise à sa source (idempotent)",
    responses=erreurs(401, 404, 422, 501),
)
async def creer_comparaison(demande: DemandeComparaison, request: Request) -> Ecart:
    """Identifiant dérivé du couple (source, reprise) : une seconde demande rend la même ressource, en 200."""
    identifiant = identifiant_comparaison(demande.video_source, demande.video_reprise)
    existant = base.lire(TYPE_DOCUMENT, identifiant)
    if existant is not None:
        return Ecart.model_validate(existant)
    videos: list[Video] = []
    for cle in (demande.video_source, demande.video_reprise):
        brut = base.lire("video", cle)
        if brut is None:
            raise ErreurApi("introuvable", f"La vidéo {cle} n'est pas connue du service.", 404)
        videos.append(Video.model_validate(brut))
    mode = mode_courant(request)
    ecart = calculer_ecart(
        videos[0], videos[1], mode=mode, enregistre_le=base.maintenant() if mode == "enregistre" else None
    )
    base.ecrire(TYPE_DOCUMENT, identifiant, ECART_V1, ecart.model_dump(mode="json"))
    return ecart


@routeur.get(
    "/comparaisons/{id}",
    response_model=Ecart,
    summary="Une comparaison : opérations au mot, écarts de légende et de texte à l'écran",
    responses=erreurs(404, 422, 501),
)
async def lire_comparaison(id: str) -> Ecart:
    """Écart `ecart.v1` : opérations retire, ajoute, remplace avec positions, jamais un verdict."""
    brut = base.lire(TYPE_DOCUMENT, id)
    if brut is None:
        raise ErreurApi("introuvable", f"La comparaison {id} n'existe pas.", 404)
    return Ecart.model_validate(brut)
