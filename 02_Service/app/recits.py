"""Regroupement en récits : une phrase surveillée = un récit, une recherche = un récit.

Règle de la fiche S05 : une vidéo appartient au récit d'une phrase quand cette phrase, normalisée par
`mots.v1`, figure parmi ses `requetes_trouvees`. Une vidéo trouvée par deux phrases compte dans les
deux récits et une seule fois dans le total.

Les phrases viennent des documents `cas` en base (clé `phrases`, ou `phrase` ; facultatifs : `requete`,
`fenetre` {debut, fin}, `enregistre_le`) ; à défaut, des `requetes_trouvees` des vidéos.

Une recherche (F020) écrit un document `recherche-…` avec `pivot` (le premier noyau, sinon la première
phrase) et `variantes` (tous les noyaux et phrases cherchés) : c'est une seule entrée, de clé
`cle_phrase(pivot)`, dont les vidéos sont celles qu'au moins une variante a trouvées, comptées une fois.
Si la clé du pivot est celle d'une phrase du cas, l'entrée du cas garde la priorité et gagne les variantes ;
deux clés différentes (« pouvoir achat » et « le pouvoir d'achat ») restent deux récits.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app import base
from app.cas import CAS_V1
from app.mesures import mesures_de_volume
from app.modeles import (
    VIDEO_V1,
    Fenetre,
    Mesure,
    PlusAncienneVersion,
    Radar,
    Recit,
    Segment,
    SousRecherche,
    Video,
)
from app.mots import normaliser
from app.vitesse import mesures_de_vitesse

journal = logging.getLogger("tete_de_brut")

TYPE_CAS = "cas"
TYPE_VIDEO = "video"

NON_CHERCHE = (
    "autres plateformes que instagram, tiktok et youtube",
    "vidéos supprimées",
    "comptes privés",
    "résultats hors de la fenêtre de la requête",
    "résultats au-delà des résultats consultés",
)


def verifier_cas(document: Any) -> str | None:
    """Raison en clair si un document `cas` est mal formé, sinon `None` (le cas sert)."""
    if not isinstance(document, dict):
        return "le document n'est pas un objet"
    phrases = document.get("phrases")
    if phrases is not None and (
        not isinstance(phrases, list) or not all(isinstance(p, str) and p.strip() for p in phrases)
    ):
        return "phrases n'est pas une liste de textes non vides"
    phrase = document.get("phrase")
    if phrase is not None and not (isinstance(phrase, str) and phrase.strip()):
        return "phrase n'est pas un texte non vide"
    pivot = document.get("pivot")
    if pivot is not None and not (isinstance(pivot, str) and pivot.strip()):
        return "pivot n'est pas un texte non vide"
    variantes = document.get("variantes")
    if variantes is not None and (
        not isinstance(variantes, list) or not all(isinstance(v, str) and v.strip() for v in variantes)
    ):
        return "variantes n'est pas une liste de textes non vides"
    noyaux = document.get("noyaux")
    if noyaux is not None and (not isinstance(noyaux, list) or not all(isinstance(n, str) for n in noyaux)):
        return "noyaux n'est pas une liste de textes"
    requete = document.get("requete")
    if requete is not None and not isinstance(requete, str):
        return "requete n'est pas un texte"
    try:
        if document.get("fenetre"):
            Fenetre.model_validate(document["fenetre"])
        if document.get("enregistre_le"):
            if datetime.fromisoformat(document["enregistre_le"]).tzinfo is None:
                return "enregistre_le sans fuseau horaire"
    except (ValueError, TypeError) as exc:
        return f"fenêtre ou date illisible ({type(exc).__name__})"
    return None


def cle_phrase(phrase: str) -> str:
    """Forme normalisée `mots.v1` d'une phrase, pour comparer et dériver l'identifiant."""
    return " ".join(normaliser(phrase))


def identifiant_recit(phrase: str) -> str:
    """Identifiant stable dérivé de la phrase normalisée."""
    return "recit-" + hashlib.sha256(cle_phrase(phrase).encode("utf-8")).hexdigest()[:12]


def recherche_de(document: dict[str, Any]) -> tuple[str, list[str]] | None:
    """(pivot, variantes) d'un document écrit par une recherche, `None` pour une phrase ordinaire du cas."""
    variantes = [v for v in (document.get("variantes") or []) if isinstance(v, str) and v.strip()]
    pivot = document.get("pivot")
    if not (isinstance(pivot, str) and pivot.strip()):
        pivot = variantes[0] if variantes else None
    if pivot is None:
        return None
    return pivot, reunir_variantes([pivot], variantes)


def cles_du_recit(details: dict[str, Any]) -> set[str]:
    """Clés normalisées d'un récit : celle de sa phrase surveillée et celles de ses variantes."""
    return {cle_phrase(details["phrase"]), *(cle_phrase(v) for v in details.get("variantes") or [])}


def reunir_variantes(*listes: Iterable[str]) -> list[str]:
    """Variantes réunies dans l'ordre, sans doublon une fois normalisées."""
    vues: dict[str, str] = {}
    for liste in listes:
        for variante in liste:
            vues.setdefault(cle_phrase(variante), variante)
    return list(vues.values())


def phrases_surveillees(cas: Iterable[dict[str, Any]], videos: Sequence[Video]) -> dict[str, dict[str, Any]]:
    """Phrases surveillées (clé normalisée vers phrase, requête, fenêtre, variantes), dans l'ordre d'arrivée.

    Un document de recherche (`pivot`, `variantes`) compte pour une seule entrée ; si le pivot est aussi une
    phrase du cas, l'entrée du cas garde la priorité (phrase, requête, fenêtre) et gagne les variantes.
    """
    phrases: dict[str, dict[str, Any]] = {}
    for document in cas:
        recherche = recherche_de(document)
        if recherche is not None:
            pivot, variantes = recherche
            cle = cle_phrase(pivot)
            existant = phrases.get(cle)
            if existant is None:
                phrases[cle] = {
                    "phrase": pivot,
                    "requete": document.get("requete"),
                    "fenetre": document.get("fenetre"),
                    "variantes": variantes,
                    "noyaux": list(document.get("noyaux") or []),
                    "de_recherche": True,
                }
            else:
                existant["variantes"] = reunir_variantes(existant.get("variantes") or [], variantes)
                existant["noyaux"] = reunir_variantes(
                    existant.get("noyaux") or [], document.get("noyaux") or []
                )
            continue
        brutes = list(document.get("phrases") or [])
        if document.get("phrase"):
            brutes.append(document["phrase"])
        for phrase in brutes:
            cle = cle_phrase(phrase)
            existant = phrases.get(cle)
            if existant is None:
                phrases[cle] = {
                    "phrase": phrase,
                    "requete": document.get("requete"),
                    "fenetre": document.get("fenetre"),
                    "variantes": None,
                }
            elif existant.get("de_recherche"):  # la phrase du cas prend la place du pivot de la recherche
                phrases[cle] = {
                    "phrase": phrase,
                    "requete": document.get("requete"),
                    "fenetre": document.get("fenetre"),
                    "variantes": existant["variantes"],
                    "noyaux": existant["noyaux"],
                }
    if not phrases:
        for video in videos:
            for phrase in video.requetes_trouvees:
                phrases.setdefault(
                    cle_phrase(phrase),
                    {"phrase": phrase, "requete": None, "fenetre": None, "variantes": None},
                )
    return phrases


def videos_du_recit(cles: str | Collection[str], videos: Sequence[Video]) -> list[Video]:
    """Vidéos dont les requêtes trouvées contiennent une des clés, de la plus ancienne à la plus récente.

    Une vidéo trouvée par plusieurs variantes d'un même récit compte une fois.
    """
    ensemble = {cles} if isinstance(cles, str) else set(cles)
    trouvees = [v for v in videos if any(cle_phrase(r) in ensemble for r in v.requetes_trouvees)]
    return sorted(trouvees, key=lambda v: (v.publie_le, v.identifiant))


def fenetre_de(videos: Sequence[Video], declaree: dict[str, Any] | None, calcule_le: datetime) -> Fenetre:
    """Fenêtre de la requête : celle du cas si elle est déclarée, sinon l'étendue des vidéos trouvées."""
    if declaree:
        return Fenetre.model_validate(declaree)
    if videos:
        return Fenetre(debut=videos[0].publie_le, fin=max(v.publie_le for v in videos))
    return Fenetre(debut=calcule_le, fin=calcule_le)


def mesures_du_recit(videos: Sequence[Video], fenetre: Fenetre, calcule_le: datetime) -> list[Mesure]:
    """Point d'appel des mesures d'un récit.

    Volume sur la fenêtre de la requête, puis vitesse sur 48 h et 7 jours avant `calcule_le` (S06).
    """
    return [*mesures_de_volume(videos, fenetre), *mesures_de_vitesse(videos, calcule_le)]


def requete_en_clair(phrase: str, fenetre: Fenetre, declaree: str | None) -> str:
    """Requête envoyée à Oriane, lisible : phrase exacte, niveau et fenêtre."""
    if declaree:
        return declaree
    return (
        f"phrase exacte « {phrase} », niveau default, "
        f"du {fenetre.debut.date().isoformat()} au {fenetre.fin.date().isoformat()}"
    )


def construire_recit(
    details: dict[str, Any],
    videos: Sequence[Video],
    calcule_le: datetime,
    mode: str,
    enregistre_le: datetime | None,
    ignores: Sequence[str] = (),
) -> Recit:
    """Un récit `recit.v1` pour une phrase surveillée ou pour une recherche (pivot et variantes)."""
    phrase = details["phrase"]
    variantes = details.get("variantes")
    trouvees = videos_du_recit(cles_du_recit(details), videos)
    fenetre = fenetre_de(trouvees, details.get("fenetre"), calcule_le)
    plus_ancienne = (
        PlusAncienneVersion(video=trouvees[0].identifiant, publie_le=trouvees[0].publie_le)
        if trouvees
        else None
    )
    return Recit(
        mode=mode,  # type: ignore[arg-type]
        enregistre_le=enregistre_le,
        identifiant=identifiant_recit(phrase),
        phrase_surveillee=phrase,
        requete_en_clair=requete_en_clair(phrase, fenetre, details.get("requete")),
        videos=[v.identifiant for v in trouvees],
        mesures=mesures_du_recit(trouvees, fenetre, calcule_le),
        plus_ancienne_version=plus_ancienne,
        non_cherche=[Segment(type="libelle", texte=t) for t in (*NON_CHERCHE, *ignores)],
        calcule_le=calcule_le,
        variantes=list(variantes) if variantes else None,
        sous_recherches=_sous_recherches(details, trouvees) if variantes else None,
    )


def _sous_recherches(details: dict[str, Any], trouvees: Sequence[Video]) -> list[SousRecherche]:
    """Chaque variante avec le nombre de vidéos du récit qu'elle a trouvées (aucun appel supplémentaire)."""
    noyaux = {cle_phrase(n) for n in details.get("noyaux") or []}
    sous: list[SousRecherche] = []
    for variante in details["variantes"]:
        cle = cle_phrase(variante)
        sous.append(
            SousRecherche(
                libelle=variante,
                type="mots" if cle in noyaux else "exacte",
                videos=sum(1 for v in trouvees if any(cle_phrase(r) == cle for r in v.requetes_trouvees)),
            )
        )
    return sous


def _enregistre_le(cas: Sequence[dict[str, Any]], videos: Sequence[Video], repli: datetime) -> datetime:
    """Date du cas rejoué : celle du cas, sinon la plus récente des vidéos, sinon l'heure du calcul."""
    dates = [datetime.fromisoformat(c["enregistre_le"]) for c in cas if c.get("enregistre_le")]
    dates += [v.enregistre_le for v in videos if v.enregistre_le]
    return max(dates) if dates else repli


def lire_videos(documents: Iterable[dict[str, Any]]) -> list[Video]:
    """Vidéos des documents, tolérantes à une `pertinence` mal formée.

    Une annotation de pertinence qui ne valide pas est écartée pour cette vidéo seule (rendue sans
    pertinence) et signalée au journal par l'identifiant de la vidéo, jamais par son contenu. Tout autre
    défaut du document lève comme avant.
    """
    videos = []
    for document in documents:
        try:
            videos.append(Video.model_validate(document))
        except ValidationError:
            if "pertinence" not in document:
                raise
            sans_pertinence = {cle: valeur for cle, valeur in document.items() if cle != "pertinence"}
            videos.append(Video.model_validate(sans_pertinence))  # lève si le défaut est ailleurs
            journal.warning("pertinence mal formée ignorée pour la vidéo %s", document.get("identifiant"))
    return videos


def calculer_recits(mode: str, calcule_le: datetime | None = None) -> tuple[list[Recit], datetime]:
    """Récits calculés sur les vidéos et cas en base, avec la date du calcul."""
    calcule_le = calcule_le or datetime.fromisoformat(base.maintenant())
    videos = lire_videos(base.lister(TYPE_VIDEO))
    cas, ignores = [], []
    for document in base.lister(TYPE_CAS):
        raison = verifier_cas(document)
        if raison is None:
            cas.append(document)
        else:
            ignores.append(f"cas ignoré : {raison}")
    enregistre_le = _enregistre_le(cas, videos, calcule_le) if mode == "enregistre" else None
    recits = [
        construire_recit(details, videos, calcule_le, mode, enregistre_le, ignores)
        for details in phrases_surveillees(cas, videos).values()
    ]
    return recits, calcule_le


def calculer_radar(mode: str, raison: str) -> Radar:
    """Radar : les récits, la date du calcul, le mode et sa raison."""
    recits, calcule_le = calculer_recits(mode)
    enregistre_le = recits[0].enregistre_le if recits else None
    if mode == "enregistre" and enregistre_le is None:
        enregistre_le = calcule_le
    return Radar(
        mode=mode,  # type: ignore[arg-type]
        enregistre_le=enregistre_le,
        recits=recits,
        calcule_le=calcule_le,
        raison=raison,
    )


@dataclass(frozen=True)
class RecitSupprime:
    """Ce qu'une suppression a retiré : la phrase, le sort des vidéos et la date du cas rejoué."""

    phrase: str
    videos_retirees: int
    videos_conservees: int
    enregistre_le: datetime


def _sans_la_phrase(document: dict[str, Any], cle: str) -> dict[str, Any] | None:
    """Le document `cas` privé de la phrase, `None` s'il ne la porte pas.

    Un document de recherche dont le pivot est la phrase part en entier (reste vide).
    """
    recherche = recherche_de(document)
    if recherche is not None:
        return {} if cle_phrase(recherche[0]) == cle else None
    phrases = document.get("phrases")
    unique = document.get("phrase")
    porte_liste = isinstance(phrases, list) and any(cle_phrase(p) == cle for p in phrases)
    porte_unique = isinstance(unique, str) and cle_phrase(unique) == cle
    if not (porte_liste or porte_unique):
        return None
    reste = dict(document)
    if porte_liste:
        reste["phrases"] = [p for p in phrases if cle_phrase(p) != cle]
    if porte_unique:
        reste.pop("phrase")
    return reste


def supprimer_recit(identifiant: str) -> RecitSupprime | None:
    """Retire un récit : sa phrase (ou les variantes de sa recherche) et les vidéos devenues orphelines.

    Rend `None` si aucune phrase surveillée ne porte cet identifiant. Une vidéo trouvée aussi par une autre
    phrase est conservée, et une variante qui est aussi la phrase d'un autre récit reste sur ses vidéos. Le
    fichier du cas sur disque n'est pas modifié. Lectures et écritures forment une seule transaction : une
    interruption ne laisse rien à moitié, et aucune écriture concurrente ne s'intercale.
    """
    maintenant = datetime.fromisoformat(base.maintenant())
    with base.transaction() as transaction:
        documents_cas = transaction.lister_avec_identifiants(TYPE_CAS)
        documents_video = transaction.lister_avec_identifiants(TYPE_VIDEO)
        valides = [d for _, d in documents_cas if verifier_cas(d) is None]
        videos = lire_videos(d for _, d in documents_video)
        entrees = phrases_surveillees(valides, videos)
        cible = next(
            (
                (cle, details)
                for cle, details in entrees.items()
                if identifiant_recit(details["phrase"]) == identifiant
            ),
            None,
        )
        if cible is None:
            return None
        cle, details = cible
        phrase = details["phrase"]
        # Clés à retirer des vidéos : celles du récit, sauf celles que porte aussi un autre récit.
        a_retirer = cles_du_recit(details)
        for autre_cle, autre in entrees.items():
            if autre_cle != cle:
                a_retirer -= cles_du_recit(autre)
        enregistre_le = _enregistre_le(valides, videos, maintenant)

        for id_cas, document in documents_cas:
            if verifier_cas(document) is not None:
                continue
            reste = _sans_la_phrase(document, cle)
            if reste is None:
                continue
            if reste.get("phrases") or reste.get("phrase"):
                transaction.ecrire(TYPE_CAS, id_cas, CAS_V1, reste)
            else:
                transaction.supprimer(TYPE_CAS, id_cas)

        retirees = conservees = 0
        for id_video, document in documents_video:
            trouvees = document.get("requetes_trouvees") or []
            if not any(cle_phrase(r) in a_retirer for r in trouvees):
                continue
            restantes = [r for r in trouvees if cle_phrase(r) not in a_retirer]
            if restantes:
                transaction.ecrire(
                    TYPE_VIDEO, id_video, VIDEO_V1, {**document, "requetes_trouvees": restantes}
                )
                conservees += 1
            else:
                transaction.supprimer(TYPE_VIDEO, id_video)
                retirees += 1
    return RecitSupprime(phrase, retirees, conservees, enregistre_le)
