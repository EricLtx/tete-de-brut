"""Recherche à la demande (S13) : préparer une question, puis la lancer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.modeles import DemandeRecherche, Erreur, Recherche, ResultatRecherche
from app.recherche import executer, preparer
from app.routes import erreurs

routeur = APIRouter(tags=["recherches"])

CODES_PREPARER = erreurs(401, 422, 501)
CODES_LANCER = {
    **erreurs(401, 404, 422, 501),
    503: {
        "model": Erreur,
        "description": (
            "oriane_injoignable : Oriane n'a pas répondu utilement (première panne) ; après deux pannes "
            "de suite, un 402 ou le plafond de crédits du jour, le service passe en mode enregistré et "
            "répond depuis le cas (201 ou 409), sans 503."
        ),
    },
    409: {
        "model": Erreur,
        "description": (
            "recherche_indisponible : en mode enregistré, seules les phrases du cas sont servies "
            "(« Mode enregistré : seules les phrases du cas sont servies »)."
        ),
    },
}


@routeur.post(
    "/recherches/preparer",
    response_model=Recherche,
    summary="Préparer une recherche : question ou lien traduits en filtres, sans appel à Oriane",
    responses=CODES_PREPARER,
)
async def preparer_recherche(demande: DemandeRecherche, request: Request) -> Recherche:
    """Traduit `{"question": …}` en `recherche.v1` : filtres affichés avant lancement, requête en clair, coût.

    Une question libre est reformulée par le modèle de langue quand sa clé est configurée (champ
    `reformulation`). Aucun appel à Oriane, aucun crédit dépensé, rien d'écrit. Une recherche refusée
    (RG-02 : le seul nom d'une personne, par exemple) rend 200 avec `refus` renseigné et un coût de 0 :
    l'écran affiche `refus.detail` et n'offre pas de lancer. Une question vide rend 422 `validation`.
    """
    return await run_in_threadpool(preparer, demande.question, request.app.state.config)


@routeur.post(
    "/recherches",
    response_model=ResultatRecherche,
    status_code=201,
    summary="Lancer une recherche : récit ajouté au radar (phrase) ou vidéo retrouvée (lien)",
    responses=CODES_LANCER,
)
async def lancer_recherche(demande: DemandeRecherche, request: Request) -> ResultatRecherche:
    """Prépare puis exécute (une page chez Oriane), même corps que `/recherches/preparer`.

    Type `phrase` : écrit les vidéos, ajoute le récit de la phrase au radar (`GET /v1/radar` le sert
    ensuite) et le rend dans `recit`. Type `lien` : rend dans `video` la vidéo du lien (404 `introuvable`
    si Oriane ne la retrouve pas). Une recherche refusée rend 422 `validation` avec le libellé du refus
    dans `detail`. En mode enregistré, rien n'est envoyé : une phrase du cas rend son récit, une autre
    phrase rend 409 `recherche_indisponible`, un lien hors du cas rend 404 `introuvable`.
    """
    return await executer(request.app, demande.question)
