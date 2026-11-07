"""Acquisition des vidéos du cas : direct (Oriane) ou enregistré, avec bascule annoncée et raisonnée.

Le service obtient les vidéos en direct par `rechercher` (S03) pour les phrases du cas, ou depuis le
cas enregistré. Il bascule seul en `enregistre`, sans retour automatique, dans trois cas : deux
pannes d'Oriane de suite, un 402, le plafond de crédits du jour. La configuration décide aussi du mode
(`MODE_DONNEES=enregistre`, ou clé absente). La bascule remplace `app.state.config` par une copie
qui porte la raison : toutes les routes lisent alors le même mode et la même raison.
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime

from fastapi import FastAPI

from app import base, cas
from app.config import Configuration
from app.modeles import CoutActualisation, Radar
from app.oriane import (
    CREDITS_PAR_PAGE_DEFAULT,
    ROUTE_JOURNAL,
    CreditsEpuises,
    OrianeInjoignable,
    RequeteInvalide,
    rechercher,
)
from app.recits import calculer_radar

journal = logging.getLogger("tete_de_brut")

ECHECS_AVANT_BASCULE = 2
# Débuts de raison de `rechercher` qui disent « Oriane n'a pas répondu » (et non « la requête est fausse »).
PANNES = ("expiration", "Oriane injoignable", "Oriane a répondu")
ROUTE_BASCULE = "acquisition.bascule"
METHODE_COUT = "15 crédits par page de 100 résultats au niveau default (estimation)"
METHODE_SANS_APPEL = "aucun appel à Oriane : le cas enregistré est rejoué"


@dataclasses.dataclass
class Suivi:
    """Nombre de pannes d'Oriane consécutives, porté par l'application."""

    pannes_de_suite: int = 0


def suivi_de(app: FastAPI) -> Suivi:
    """Suivi de l'application, créé au premier usage."""
    if not hasattr(app.state, "suivi_acquisition"):
        app.state.suivi_acquisition = Suivi()
    return app.state.suivi_acquisition


def credits_du_jour() -> int:
    """Crédits Oriane estimés dépensés aujourd'hui (UTC), d'après le journal des appels."""
    aujourdhui = datetime.now(UTC).date().isoformat()
    total = 0.0
    for ligne in base.lire_journal(100_000):
        if ligne["route"] == ROUTE_JOURNAL and str(ligne["heure"]).startswith(aujourdhui):
            total += ligne["credits_estimes"] or 0
    return round(total)


def enregistre_le_courant(config: Configuration) -> datetime:
    """Date du cas rejoué si on la connaît, sinon l'instant présent (une réponse enregistrée en exige une)."""
    try:
        rejoue = cas.lire_cas(config)
    except cas.CasInvalide:
        rejoue = None
    return rejoue.enregistre_le if rejoue else datetime.now(UTC)


def basculer(app: FastAPI, raison: str) -> Configuration:
    """Passe le service en mode enregistré avec sa raison, laisse une ligne au journal, rend la config."""
    config = dataclasses.replace(app.state.config, bascule=raison)
    app.state.config = config
    cas.oublier_chargement()
    base.consigner(route=ROUTE_BASCULE, cible=raison, mode="enregistre")
    journal.warning("bascule en mode enregistré : %s", raison)
    return config


def _radar_enregistre(config: Configuration) -> Radar:
    """Radar du cas enregistré, chargé en base d'abord ; aucun appel, donc aucun crédit."""
    cas.charger(config, avec_videos=True)
    radar = calculer_radar(config.mode, config.raison)
    cout = CoutActualisation(credits_estimes=0, methode=METHODE_SANS_APPEL)
    return radar.model_copy(update={"cout_actualisation": cout})


async def actualiser(app: FastAPI) -> Radar:
    """Acquiert les vidéos du cas et rend le radar, avec le coût estimé de l'acquisition.

    En mode enregistré, rejoue le cas sans appel. En direct : refuse une phrase de moins de trois mots
    (RG-02) et une requête sans phrase avant tout appel, vérifie le plafond de crédits du jour, puis
    appelle Oriane. Une première panne remonte en 503 ; la seconde de suite, un 402 ou le plafond
    basculent en mode enregistré et rendent le radar enregistré avec la raison.
    """
    config: Configuration = app.state.config
    if config.mode == "enregistre":
        return _radar_enregistre(config)

    try:
        rejoue = cas.lire_cas(config)
    except cas.CasInvalide as exc:
        raise RequeteInvalide(f"cas enregistré refusé : {exc.raison}") from exc
    if rejoue is None:
        raise RequeteInvalide("aucun cas enregistré : les phrases à surveiller sont inconnues")
    raison_rg02 = cas.verifier_phrases(rejoue.phrases)
    if raison_rg02:
        raise RequeteInvalide(raison_rg02)

    depenses = credits_du_jour()
    if depenses + CREDITS_PAR_PAGE_DEFAULT > config.plafond_credits_jour:
        basculer(
            app,
            f"plafond de crédits du jour atteint ({depenses} sur {config.plafond_credits_jour}) : "
            "le service rejoue le cas enregistré",
        )
        return _radar_enregistre(app.state.config)

    suivi = suivi_de(app)
    try:
        resultat = await rechercher(
            rejoue.phrases,
            rejoue.comptes,
            rejoue.fenetre,
            config=config,
            plateformes=rejoue.plateformes,
            transport=getattr(app.state, "transport_oriane", None),
        )
    except CreditsEpuises:
        basculer(app, "crédits Oriane épuisés (402) : le service rejoue le cas enregistré")
        return _radar_enregistre(app.state.config)
    except OrianeInjoignable as exc:
        if not exc.raison.startswith(PANNES):
            raise  # clé refusée, requête refusée : une panne de configuration, pas de bascule
        suivi.pannes_de_suite += 1
        if suivi.pannes_de_suite < ECHECS_AVANT_BASCULE:
            raise
        basculer(
            app,
            f"Oriane injoignable : {suivi.pannes_de_suite} échecs de suite (dernier : {exc.raison}) ; "
            "le service rejoue le cas enregistré",
        )
        suivi.pannes_de_suite = 0
        return _radar_enregistre(app.state.config)

    suivi.pannes_de_suite = 0
    cas.oublier_chargement()
    cas.charger(config, avec_videos=False)
    radar = calculer_radar(config.mode, config.raison)
    cout = CoutActualisation(credits_estimes=resultat.credits_estimes, methode=METHODE_COUT)
    return radar.model_copy(update={"cout_actualisation": cout})
