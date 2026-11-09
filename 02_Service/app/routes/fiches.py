"""Fiche de vérification, décision et export (S08)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from app import base
from app.ecart import TYPE_DOCUMENT as TYPE_ECART
from app.erreurs import ErreurApi, mode_courant
from app.export import exporter
from app.fiche import TYPE_DOCUMENT, construire_fiche, identifiant_fiche, modifier
from app.fiche import decider as decider_fiche
from app.modeles import FICHE_V1, DemandeDecision, DemandeFiche, Ecart, Fiche, ModificationFiche, Video
from app.recits import lire_videos
from app.routes import erreurs

routeur = APIRouter(tags=["fiches"])


def _lire(id: str) -> Fiche:
    brut = base.lire(TYPE_DOCUMENT, id)
    if brut is None:
        raise ErreurApi("introuvable", f"La fiche {id} n'existe pas.", 404)
    return Fiche.model_validate(brut)


def _enregistrer(fiche: Fiche, geste: str) -> Fiche:
    """Écrit la fiche et consigne le geste au journal des appels (identifiant seul, aucun texte)."""
    base.ecrire(TYPE_DOCUMENT, fiche.identifiant, FICHE_V1, fiche.model_dump(mode="json"))
    base.consigner(route=f"fiche:{geste}", cible=fiche.identifiant, mode=fiche.mode)
    return fiche


@routeur.post(
    "/fiches",
    response_model=Fiche,
    status_code=201,
    summary="Créer la fiche de vérification d'une comparaison",
    responses=erreurs(401, 404, 422, 501),
)
async def creer_fiche(demande: DemandeFiche, request: Request, response: Response) -> Fiche:
    """Fiche `fiche.v1` construite par le gabarit : versions à trancher, constat vide, aucune décision."""
    # Une fiche par comparaison : une seconde demande rend la fiche existante (200), gestes compris.
    existante = base.lire(TYPE_DOCUMENT, identifiant_fiche(demande.comparaison))
    if existante is not None:
        response.status_code = 200
        return Fiche.model_validate(existante)
    brut = base.lire(TYPE_ECART, demande.comparaison)
    if brut is None:
        raise ErreurApi("introuvable", f"La comparaison {demande.comparaison} n'existe pas.", 404)
    comparaison = Ecart.model_validate(brut)
    videos: list[Video] = []
    for cle in (comparaison.video_source, comparaison.video_reprise):
        video = base.lire("video", cle)
        if video is None:
            raise ErreurApi("introuvable", f"La vidéo {cle} n'est pas connue du service.", 404)
        videos.extend(lire_videos([video]))
    mode = mode_courant(request)
    enregistre_le = None
    if mode == "enregistre":
        enregistre_le = (
            comparaison.enregistre_le.isoformat() if comparaison.enregistre_le else base.maintenant()
        )
    # Le résumé peut appeler un modèle de langue (S10) : hors de la boucle, sans bloquer les autres.
    fiche = await run_in_threadpool(
        construire_fiche,
        comparaison,
        videos[0],
        videos[1],
        mode=mode,
        enregistre_le=enregistre_le,
        heure=base.maintenant(),
    )
    return _enregistrer(fiche, "creation")


@routeur.get(
    "/fiches/{id}",
    response_model=Fiche,
    summary="Une fiche de vérification",
    responses=erreurs(404, 422, 501),
)
async def lire_fiche(id: str) -> Fiche:
    """Fiche `fiche.v1` avec son journal de gestes."""
    return _lire(id)


@routeur.patch(
    "/fiches/{id}",
    response_model=Fiche,
    summary="Trancher les versions et écrire le constat",
    responses=erreurs(401, 404, 422, 501),
)
async def modifier_fiche(id: str, modification: ModificationFiche) -> Fiche:
    """Le journaliste tranche chaque version (confirmée, écartée) et écrit le constat ; rien n'est filtré."""
    fiche = modifier(_lire(id), modification, heure=base.maintenant())
    return _enregistrer(fiche, "modification")


@routeur.post(
    "/fiches/{id}/decision",
    response_model=Fiche,
    summary="Enregistrer la décision : à vérifier, ne pas amplifier, prêt à traiter",
    responses=erreurs(401, 404, 422, 501),
)
async def decider(id: str, demande: DemandeDecision) -> Fiche:
    """Décision `decision.v1` prise par une personne ; l'heure est posée par le service."""
    fiche = decider_fiche(_lire(id), demande, heure=base.maintenant())
    return _enregistrer(fiche, "decision")


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
    fiche = _lire(id)
    page = exporter(fiche, exporte_le=base.maintenant())
    base.consigner(route="fiche:export", cible=fiche.identifiant, mode=fiche.mode)
    return HTMLResponse(page)
