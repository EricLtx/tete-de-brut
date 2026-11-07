"""Barre d'état, journal des appels et actualisation du radar (S04)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app import __version__, acquisition, base, cas
from app.modeles import Etat, Journal, Radar
from app.routes import erreurs

routeur = APIRouter(tags=["état"])


@routeur.get(
    "/etat",
    response_model=Etat,
    summary="État du service : mode, raison, crédits du jour, version et contrat",
    responses=erreurs(501),
)
async def lire_etat(request: Request) -> Etat:
    """Mode (`direct` ou `enregistre`) et sa raison, date du cas rejoué, crédits du jour sur plafond."""
    config = request.app.state.config
    raison, enregistre_le = config.raison, None
    if config.mode == "enregistre":
        try:
            rejoue = cas.charger(config, avec_videos=True)
        except cas.CasInvalide as exc:
            rejoue, raison = None, f"{raison} (cas enregistré refusé : {exc.raison})"
        else:
            if rejoue is None:
                raison = f"{raison} (aucun cas enregistré)"
        enregistre_le = rejoue.enregistre_le if rejoue else None
    return Etat(
        mode=config.mode,
        raison=raison,
        enregistre_le=enregistre_le,
        credits_du_jour=acquisition.credits_du_jour(),
        plafond_credits_jour=config.plafond_credits_jour,
        version=__version__,
    )


@routeur.get(
    "/journal",
    response_model=Journal,
    summary="Journal des appels, le plus récent d'abord",
    responses=erreurs(422, 501),
)
async def lire_journal(
    request: Request,
    limite: int = Query(default=100, ge=1, le=1000, description="Nombre de lignes rendues."),
) -> Journal:
    """Chaque appel Oriane et chaque geste, sans réponse brute ni clé."""
    config = request.app.state.config
    enregistre_le = acquisition.enregistre_le_courant(config) if config.mode == "enregistre" else None
    return Journal(mode=config.mode, enregistre_le=enregistre_le, entrees=base.lire_journal(limite))


@routeur.post(
    "/radar/actualiser",
    response_model=Radar,
    summary="Actualiser le radar par une requête Oriane en direct",
    responses=erreurs(401, 422, 501, 503),
)
async def actualiser_radar(request: Request) -> Radar:
    """Une requête Oriane en direct (coût affiché avant le geste) ; bascule en mode enregistré si besoin."""
    return await acquisition.actualiser(request.app)
