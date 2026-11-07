"""Regroupement en récits : une phrase surveillée = un récit.

Règle de la fiche S05 : une vidéo appartient au récit d'une phrase quand cette phrase, normalisée par
`mots.v1`, figure parmi ses `requetes_trouvees`. Une vidéo trouvée par deux phrases compte dans les
deux récits et une seule fois dans le total.

Les phrases viennent des documents `cas` en base (clé `phrases`, ou `phrase` ; facultatifs : `requete`,
`fenetre` {debut, fin}, `enregistre_le`) ; à défaut, des `requetes_trouvees` des vidéos.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app import base
from app.cas import CAS_V1
from app.mesures import mesures_de_volume
from app.modeles import VIDEO_V1, Fenetre, Mesure, PlusAncienneVersion, Radar, Recit, Segment, Video
from app.mots import normaliser
from app.vitesse import mesures_de_vitesse

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


def phrases_surveillees(cas: Iterable[dict[str, Any]], videos: Sequence[Video]) -> dict[str, dict[str, Any]]:
    """Phrases surveillées (clé normalisée vers phrase, requête, fenêtre), dans l'ordre d'apparition."""
    phrases: dict[str, dict[str, Any]] = {}
    for document in cas:
        brutes = list(document.get("phrases") or [])
        if document.get("phrase"):
            brutes.append(document["phrase"])
        for phrase in brutes:
            phrases.setdefault(
                cle_phrase(phrase),
                {"phrase": phrase, "requete": document.get("requete"), "fenetre": document.get("fenetre")},
            )
    if not phrases:
        for video in videos:
            for phrase in video.requetes_trouvees:
                phrases.setdefault(cle_phrase(phrase), {"phrase": phrase, "requete": None, "fenetre": None})
    return phrases


def videos_du_recit(cle: str, videos: Sequence[Video]) -> list[Video]:
    """Vidéos dont les requêtes trouvées contiennent la phrase, de la plus ancienne à la plus récente."""
    trouvees = [v for v in videos if any(cle_phrase(r) == cle for r in v.requetes_trouvees)]
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
    """Un récit `recit.v1` pour une phrase surveillée."""
    phrase = details["phrase"]
    trouvees = videos_du_recit(cle_phrase(phrase), videos)
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
    )


def _enregistre_le(cas: Sequence[dict[str, Any]], videos: Sequence[Video], repli: datetime) -> datetime:
    """Date du cas rejoué : celle du cas, sinon la plus récente des vidéos, sinon l'heure du calcul."""
    dates = [datetime.fromisoformat(c["enregistre_le"]) for c in cas if c.get("enregistre_le")]
    dates += [v.enregistre_le for v in videos if v.enregistre_le]
    return max(dates) if dates else repli


def calculer_recits(mode: str, calcule_le: datetime | None = None) -> tuple[list[Recit], datetime]:
    """Récits calculés sur les vidéos et cas en base, avec la date du calcul."""
    calcule_le = calcule_le or datetime.fromisoformat(base.maintenant())
    videos = [Video.model_validate(d) for d in base.lister(TYPE_VIDEO)]
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
    """Le document `cas` privé de la phrase (`phrases`, `phrase`), `None` s'il ne la porte pas."""
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
    """Retire un récit : sa phrase des phrases surveillées, des vidéos, et les vidéos devenues orphelines.

    Rend `None` si aucune phrase surveillée ne porte cet identifiant. Une vidéo trouvée aussi par une
    autre phrase est conservée. Le fichier du cas sur disque n'est pas modifié.
    """
    maintenant = datetime.fromisoformat(base.maintenant())
    documents_cas = base.lister_avec_identifiants(TYPE_CAS)
    documents_video = base.lister_avec_identifiants(TYPE_VIDEO)
    valides = [d for _, d in documents_cas if verifier_cas(d) is None]
    videos = [Video.model_validate(d) for _, d in documents_video]
    cible = next(
        (
            (cle, details["phrase"])
            for cle, details in phrases_surveillees(valides, videos).items()
            if identifiant_recit(details["phrase"]) == identifiant
        ),
        None,
    )
    if cible is None:
        return None
    cle, phrase = cible
    enregistre_le = _enregistre_le(valides, videos, maintenant)

    for id_cas, document in documents_cas:
        if verifier_cas(document) is not None:
            continue
        reste = _sans_la_phrase(document, cle)
        if reste is None:
            continue
        if reste.get("phrases") or reste.get("phrase"):
            base.ecrire(TYPE_CAS, id_cas, CAS_V1, reste)
        else:
            base.supprimer(TYPE_CAS, id_cas)

    retirees = conservees = 0
    for id_video, document in documents_video:
        trouvees = document.get("requetes_trouvees") or []
        if not any(cle_phrase(r) == cle for r in trouvees):
            continue
        restantes = [r for r in trouvees if cle_phrase(r) != cle]
        if restantes:
            base.ecrire(TYPE_VIDEO, id_video, VIDEO_V1, {**document, "requetes_trouvees": restantes})
            conservees += 1
        else:
            base.supprimer(TYPE_VIDEO, id_video)
            retirees += 1
    return RecitSupprime(phrase, retirees, conservees, enregistre_le)
