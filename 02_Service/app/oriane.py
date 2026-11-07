"""Appel unique à Oriane : construit la requête, journalise, rend des `Video` de la liste blanche.

Aucune autre fonction du service n'appelle Oriane. La réponse brute n'est jamais conservée ni
journalisée ; la clé ne sort que dans l'en-tête d'authentification de la requête.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app import base, liste_blanche
from app.config import Configuration
from app.modeles import VIDEO_V1, Fenetre, Video

journal = logging.getLogger("tete_de_brut")

TAILLE_PAGE = 100
CREDITS_PAR_PAGE_DEFAULT = 15  # estimation (F) : 15 crédits par page de 100 au niveau default
PROJECTION = "default"
TRI = "publishedAt:asc"
NOM_REQUETE = "tete-de-brut-recherche"
ROUTE_JOURNAL = "oriane.recherche"


class ErreurOriane(Exception):
    """Base des erreurs d'appel à Oriane ; `raison` est une phrase lisible, sans clé."""

    def __init__(self, raison: str):
        super().__init__(raison)
        self.raison = raison


class OrianeInjoignable(ErreurOriane):
    """Oriane n'a pas répondu utilement : expiration, authentification ou requête refusée, autre code."""


class CreditsEpuises(ErreurOriane):
    """Oriane répond 402 : plus de crédits."""


class RequeteInvalide(ErreurOriane):
    """La requête est refusée avant tout appel (aucune phrase, fenêtre inversée)."""


@dataclass(frozen=True)
class ResultatRecherche:
    """Ce que rend `rechercher` : les vidéos de la page et de quoi dire si elle est complète."""

    videos: list[Video]
    total: int | None
    ecartees: int
    code: int
    credits_estimes: int
    requete: dict[str, Any] = field(repr=False)

    @property
    def incomplete(self) -> bool:
        """Vrai si Oriane annonce plus de résultats que la page reçue (réponse 206)."""
        recus = len(self.videos) + self.ecartees
        return self.code == 206 or (self.total is not None and self.total > recus)


def _date(valeur: datetime | date) -> str:
    return (valeur.date() if isinstance(valeur, datetime) else valeur).isoformat()


def construire_corps(
    phrases: Sequence[str],
    comptes: Sequence[str] = (),
    fenetre: Fenetre | None = None,
    plateformes: Sequence[str] = (),
    comptes_exclus: Sequence[str] = (),
    identifiants_plateforme: Sequence[tuple[str, str]] = (),
) -> dict[str, Any]:
    """Corps de `POST /rest/contents/search` : une phrase exacte, dite ou écrite à l'écran.

    `comptes_exclus` écarte des comptes ; `identifiants_plateforme` (couples plateforme et identifiant)
    cherche des vidéos par leur lien, sans phrase.
    """
    nettoyees = [p.strip() for p in phrases if p and p.strip()]
    if not nettoyees and not identifiants_plateforme:
        raise RequeteInvalide("requête refusée : au moins une phrase est nécessaire")
    if any(len(p) > liste_blanche.LONGUEUR_MAX_PHRASE for p in nettoyees):
        raise RequeteInvalide(
            f"requête refusée : une phrase dépasse {liste_blanche.LONGUEUR_MAX_PHRASE} caractères"
        )
    nettoyees = list(dict.fromkeys(nettoyees))
    filtres: dict[str, Any] = {}
    filtre_compte: dict[str, Any] = {}
    if comptes:
        filtre_compte[liste_blanche.OPERATEUR_COMPTES] = [c.strip() for c in comptes]
    if comptes_exclus:
        filtre_compte[liste_blanche.OPERATEUR_COMPTES_EXCLUS] = {
            "values": [c.strip() for c in comptes_exclus],
            "operator": "or",
        }
    if filtre_compte:
        filtres[liste_blanche.FILTRE_COMPTE] = filtre_compte
    if plateformes:
        filtres[liste_blanche.FILTRE_PLATEFORME] = {liste_blanche.OPERATEUR_PLATEFORMES: list(plateformes)}
    if identifiants_plateforme:
        filtres[liste_blanche.FILTRE_IDENTIFIANT] = {
            liste_blanche.OPERATEUR_IDENTIFIANTS: [
                {"platform": plateforme, "platformId": identifiant}
                for plateforme, identifiant in identifiants_plateforme
            ]
        }
    if fenetre is not None:
        if fenetre.fin < fenetre.debut:
            raise RequeteInvalide("requête refusée : la fenêtre se termine avant de commencer")
        filtres[liste_blanche.FILTRE_DATE] = {"after": _date(fenetre.debut), "before": _date(fenetre.fin)}
    # Cadre (compte, plateforme, dates) à la racine en `and` ; « dit ou écrit » en sous-requête `or`
    # dont chaque enfant porte une phrase (`dit:<phrase>`, `ecrit:<phrase>`) : Oriane rend ces noms
    # dans `matchedQueries`. Un `or` racine s'appliquerait aussi au cadre (relevé réel du 07/11).
    enfants: list[dict[str, Any]] = []
    for phrase in nettoyees:
        groupe = {liste_blanche.OPERATEUR_PHRASES: {"values": [phrase], "operator": "or"}}
        for origine, filtre in (
            (liste_blanche.REQUETE_DIT, liste_blanche.FILTRE_TRANSCRIPTION),
            (liste_blanche.REQUETE_ECRIT, liste_blanche.FILTRE_TEXTE_ECRAN),
        ):
            enfants.append(
                {
                    "name": liste_blanche.nom_requete(origine, phrase),
                    "operator": "and",
                    "filters": {filtre: groupe},
                }
            )
    corps: dict[str, Any] = {"name": NOM_REQUETE, "operator": "and", "filters": filtres}
    if enfants:  # une recherche par lien n'a aucune phrase, donc aucune sous-requête
        corps["queries"] = [
            {"name": liste_blanche.REQUETE_DIT_OU_ECRIT, "operator": "or", "queries": enfants}
        ]
    return corps


def _phrases_du_corps(corps: dict[str, Any]) -> list[dict[str, Any]]:
    """Phrases cherchées, dans l'ordre, lues dans les sous-requêtes `dit:` du corps."""
    return [
        q["filters"][liste_blanche.FILTRE_TRANSCRIPTION][liste_blanche.OPERATEUR_PHRASES]
        for q in (corps["queries"][0]["queries"] if "queries" in corps else [])
        if liste_blanche.FILTRE_TRANSCRIPTION in q["filters"]
    ]


def _raison_400(reponse: httpx.Response) -> str:
    """Raison d'un 400 : champ et message de `error.context`, jamais le corps entier."""
    morceaux: list[str] = []
    try:
        contexte = reponse.json()["error"]["context"]
        for element in contexte if isinstance(contexte, list) else []:
            champ, message = str(element.get("field", "")), str(element.get("message", ""))
            morceaux.append(f"{champ} {message}".strip())
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    detail = " ; ".join(m for m in morceaux if m)
    return f"requête refusée : {detail}"[:400] if detail else "requête refusée"


def _consigner(
    corps: dict[str, Any],
    cible: str,
    debut: float,
    code: int | None,
    resultats: dict[str, Any],
    credits: int | None,
) -> None:
    base.consigner(
        route=ROUTE_JOURNAL,
        cible=cible,
        filtres=corps,
        projection=PROJECTION,
        resultats=resultats,
        credits_estimes=credits,
        duree_ms=round((time.monotonic() - debut) * 1000, 1),
        code=code,
        mode="direct",
    )


async def rechercher(
    phrases: Sequence[str],
    comptes: Sequence[str] = (),
    fenetre: Fenetre | None = None,
    *,
    config: Configuration,
    plateformes: Sequence[str] = (),
    comptes_exclus: Sequence[str] = (),
    identifiants_plateforme: Sequence[tuple[str, str]] = (),
    limite: int = TAILLE_PAGE,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ResultatRecherche:
    """Interroge Oriane (une page) et rend les vidéos `video.v1` de la liste blanche, écrites en base.

    Lève `RequeteInvalide` (avant tout appel), `CreditsEpuises` (402) ou `OrianeInjoignable`
    (clé absente, 401, 400, expiration, autre code). Chaque appel parti laisse une ligne au journal.
    """
    corps = construire_corps(phrases, comptes, fenetre, plateformes, comptes_exclus, identifiants_plateforme)
    cible = (
        f"POST {liste_blanche.CHEMIN_RECHERCHE}?sort={TRI}&offset=0&limit={limite}&projection={PROJECTION}"
    )
    debut = time.monotonic()
    if not config.oriane_cle:
        raise OrianeInjoignable("clé Oriane absente")
    en_tetes = {config.oriane_en_tete_auth: config.oriane_prefixe_auth + config.oriane_cle}
    parametres = {"sort": TRI, "offset": 0, "limit": limite, "projection": PROJECTION}
    try:
        async with httpx.AsyncClient(
            base_url=config.oriane_url, timeout=config.oriane_delai_s, transport=transport
        ) as client:
            reponse = await client.post(
                liste_blanche.CHEMIN_RECHERCHE, params=parametres, json=corps, headers=en_tetes
            )
    except httpx.TimeoutException as exc:
        _consigner(corps, cible, debut, None, {"erreur": "expiration"}, None)
        raise OrianeInjoignable(f"expiration après {config.oriane_delai_s:g} s") from exc
    except httpx.HTTPError as exc:
        _consigner(corps, cible, debut, None, {"erreur": "injoignable"}, None)
        raise OrianeInjoignable("Oriane injoignable") from exc

    code = reponse.status_code
    if code not in (200, 206):
        _consigner(corps, cible, debut, code, {"erreur": f"code {code}"}, None)
        if code == 401:
            raise OrianeInjoignable("authentification refusée")
        if code == 400:
            raise OrianeInjoignable(_raison_400(reponse))
        if code == 402:
            raise CreditsEpuises("crédits Oriane épuisés")
        raise OrianeInjoignable(f"Oriane a répondu avec le code {code}")

    try:
        brut = reponse.json()
        elements = brut["data"]["results"]
        total = brut.get("metadata", {}).get("pagination", {}).get("totalCount")
        if not isinstance(elements, list):
            raise TypeError("results n'est pas une liste")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        _consigner(corps, cible, debut, code, {"erreur": "réponse illisible"}, None)
        raise OrianeInjoignable("réponse d'Oriane illisible") from exc

    lue_le = datetime.now(UTC)
    phrases_cherchees = [f["values"][0] for f in _phrases_du_corps(corps)]
    videos: list[Video] = []
    ecartees = 0
    videos_brutes: list[dict[str, Any]] = []
    for element in elements:
        try:
            if not isinstance(element, dict):
                raise liste_blanche.ResultatIllisible("résultat inattendu")
            videos.append(liste_blanche.projeter(element, lue_le=lue_le, phrases=phrases_cherchees))
            videos_brutes.append(element)
        except liste_blanche.ResultatIllisible:
            ecartees += 1
    total = total if isinstance(total, int) and not isinstance(total, bool) else None
    credits = math.ceil(max(len(elements), 1) / TAILLE_PAGE) * CREDITS_PAR_PAGE_DEFAULT
    for video in videos:
        base.ecrire("video", video.identifiant, VIDEO_V1, video.model_dump(mode="json"))
    _consigner(
        corps,
        cible,
        debut,
        code,
        {
            "retournes": len(videos),
            "ecartes": ecartees,
            "total_annonce": total,
            **liste_blanche.compter_origines(videos_brutes),
        },
        credits,
    )
    if ecartees:
        journal.warning("%d résultat(s) Oriane écarté(s) : champs obligatoires absents", ecartees)
    return ResultatRecherche(
        videos=videos, total=total, ecartees=ecartees, code=code, credits_estimes=credits, requete=corps
    )
