"""Radar des récits (rempli par S05)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import base
from app.erreurs import ErreurApi
from app.modeles import Radar, Recit, SuppressionRecit
from app.recits import calculer_radar, calculer_recits, supprimer_recit
from app.routes import erreurs

routeur = APIRouter(tags=["radar"])


@routeur.get(
    "/radar",
    response_model=Radar,
    summary="Radar des récits : récits, mesures, requête en clair, mode et date du calcul",
    responses=erreurs(501),
)
async def lire_radar(request: Request) -> Radar:
    """Un récit par phrase surveillée, avec ses mesures (méthode et fenêtre) et ce qui n'a pas été cherché."""
    config = request.app.state.config
    return calculer_radar(config.mode, config.raison)


@routeur.get(
    "/recits/{id}",
    response_model=Recit,
    summary="Un récit, ses vidéos et ses mesures",
    responses=erreurs(404, 422, 501),
)
async def lire_recit(id: str, request: Request) -> Recit:
    """Récit `recit.v1` : phrase surveillée, requête en clair, plus ancienne version, non cherché."""
    recits, _ = calculer_recits(request.app.state.config.mode)
    for recit in recits:
        if recit.identifiant == id:
            return recit
    raise ErreurApi("introuvable", f"Aucun récit « {id} » dans le radar.", 404)


AVERTISSEMENT_ENREGISTRE = (
    "Mode enregistré : la suppression vaut pour la base courante ; le fichier du cas n'est pas modifié "
    "et la phrase revient au redémarrage du service si le cas est inchangé."
)


@routeur.delete(
    "/recits/{id}",
    response_model=SuppressionRecit,
    summary="Supprimer un récit : sa phrase surveillée et les vidéos qu'elle seule avait trouvées",
    responses=erreurs(401, 404, 422, 501),
)
async def supprimer_un_recit(id: str, request: Request) -> SuppressionRecit:
    """Retire la phrase des phrases surveillées et des vidéos ; une vidéo d'une autre phrase reste."""
    mode = request.app.state.config.mode
    retire = supprimer_recit(id)
    if retire is None:
        raise ErreurApi("introuvable", f"Aucun récit « {id} » dans le radar.", 404)
    base.consigner(
        route="recit:suppression",
        cible=retire.phrase,
        resultats={"videos_retirees": retire.videos_retirees, "videos_conservees": retire.videos_conservees},
        mode=mode,
    )
    return SuppressionRecit(
        mode=mode,  # type: ignore[arg-type]
        enregistre_le=retire.enregistre_le if mode == "enregistre" else None,
        identifiant=id,
        phrase_surveillee=retire.phrase,
        videos_retirees=retire.videos_retirees,
        videos_conservees=retire.videos_conservees,
        avertissement=AVERTISSEMENT_ENREGISTRE if mode == "enregistre" else None,
    )
