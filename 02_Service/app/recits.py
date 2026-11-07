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
from datetime import datetime
from typing import Any

from app import base
from app.mesures import mesures_de_volume
from app.modeles import Fenetre, Mesure, PlusAncienneVersion, Radar, Recit, Segment, Video
from app.mots import normaliser

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

    S06 : ajouter ici, après les mesures de volume, la mesure de vitesse de `app/vitesse.py`
    (vidéos par jour sur 48 h contre sur 7 jours, deux fenêtres), sans changer `Mesure`.
    """
    return mesures_de_volume(videos, fenetre)


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
