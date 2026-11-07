"""Cas enregistré : format du fichier hors Git, contrôles, chargement en base.

Le fichier JSON (`CHEMIN_CAS`, dossier `cas/` ou chemin se terminant par `.json`) a une seule forme :
`{"enregistre_le", "projection", "credits_estimes", "phrases", "comptes", "fenetre", "requete", "videos"}`
(`plateformes` facultatif). Il est écrit par `scripts/enregistrer_cas.py` avec la clé Oriane d'un humain,
et relu ici sans clé. Un champ de tiers, une image ou une vidéo font refuser le fichier, à l'écriture
comme au chargement. Toute vidéo rejouée sort en mode `enregistre`, jamais `direct`.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app import base
from app.config import Configuration
from app.liste_blanche import CHAMPS_REFUSES, CHAMPS_REFUSES_MEDIA, PREFIXES_REFUSES
from app.modeles import VIDEO_V1, Fenetre, Video
from app.mots import normaliser

CAS_V1 = "cas.v1"
TYPE_CAS = "cas"
IDENTIFIANT_CAS = "cas-principal"
NOM_FICHIER = "cas.json"
MOTS_MINIMUM = 3  # RG-02 : en l'absence de détection de noms, moins de trois mots est refusé
CHAMPS_AUTORISES = frozenset(
    {
        "enregistre_le",
        "projection",
        "credits_estimes",
        "phrases",
        "comptes",
        "plateformes",
        "fenetre",
        "requete",
        "videos",
    }
)
_MEDIA_URL = re.compile(
    r"^(https?://|data:).*(\.(jpe?g|png|gif|webp|avif|mp4|mov|webm|m4a|mp3)(\?\S*)?$|;base64,)", re.I
)
_cache_chargement: dict[tuple[str, str, int, bool], datetime] = {}


class CasInvalide(ValueError):
    """Le cas enregistré est refusé ; `raison` le dit en clair, sans clé ni donnée de tiers."""

    def __init__(self, raison: str):
        super().__init__(raison)
        self.raison = raison


@dataclass(frozen=True)
class CasEnregistre:
    """Cas relu et validé : phrases surveillées, cadre de la requête et vidéos `video.v1` rejouées."""

    enregistre_le: datetime
    phrases: list[str]
    comptes: list[str]
    plateformes: list[str]
    fenetre: Fenetre | None
    requete: str
    credits_estimes: int
    videos: list[Video]


def fichier_cas(config: Configuration) -> Path:
    """Fichier du cas : `CHEMIN_CAS` s'il se termine par `.json`, sinon `cas.json` dans ce dossier."""
    chemin = Path(config.chemin_cas)
    return chemin if chemin.suffix.lower() == ".json" else chemin / NOM_FICHIER


def verifier_phrases(phrases: Sequence[str]) -> str | None:
    """Règle RG-02 : raison du refus si une phrase compte moins de trois mots, sinon `None`."""
    if not [p for p in phrases if p and p.strip()]:
        return "aucune phrase à surveiller"
    for phrase in phrases:
        if len(normaliser(phrase or "")) < MOTS_MINIMUM:
            return (
                f"phrase refusée (RG-02) : « {phrase} » compte moins de {MOTS_MINIMUM} mots, "
                "une phrase réduite à un nom de personne n'est pas surveillée"
            )
    return None


def _parcourir(objet: Any) -> Iterator[tuple[str, Any]]:
    """Chaque couple (nom de champ, valeur) d'un objet JSON imbriqué."""
    if isinstance(objet, dict):
        for nom, valeur in objet.items():
            yield str(nom), valeur
            yield from _parcourir(valeur)
    elif isinstance(objet, list):
        for valeur in objet:
            yield from _parcourir(valeur)


def champs_refuses(document: Any) -> list[str]:
    """Noms des champs de tiers, images ou vidéos trouvés n'importe où dans le document."""
    trouves: list[str] = []
    for nom, valeur in _parcourir(document):
        if nom in CHAMPS_REFUSES or nom in CHAMPS_REFUSES_MEDIA or nom.startswith(PREFIXES_REFUSES):
            trouves.append(nom)
        elif isinstance(valeur, str) and _MEDIA_URL.search(valeur):
            trouves.append(f"{nom} (image ou vidéo)")
    return sorted(set(trouves))


def _liste_de_textes(document: dict[str, Any], nom: str) -> list[str]:
    valeur = document.get(nom, [])
    if not isinstance(valeur, list) or not all(isinstance(t, str) and t.strip() for t in valeur):
        raise CasInvalide(f"{nom} n'est pas une liste de textes non vides")
    return valeur


def valider(document: Any) -> CasEnregistre:
    """Valide un document de cas (champs, RG-02, vidéos `video.v1`) ; lève `CasInvalide` sinon."""
    if not isinstance(document, dict):
        raise CasInvalide("le cas n'est pas un objet JSON")
    refuses = champs_refuses(document)
    if refuses:
        raise CasInvalide(f"champ refusé dans le cas : {', '.join(refuses)}")
    inconnus = sorted(set(document) - CHAMPS_AUTORISES)
    if inconnus:
        raise CasInvalide(f"champ hors liste blanche dans le cas : {', '.join(inconnus)}")
    try:
        enregistre_le = datetime.fromisoformat(document["enregistre_le"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CasInvalide("enregistre_le absent ou illisible") from exc
    if enregistre_le.tzinfo is None:
        raise CasInvalide("enregistre_le sans fuseau horaire")
    phrases = _liste_de_textes(document, "phrases")
    raison = verifier_phrases(phrases)
    if raison:
        raise CasInvalide(raison)
    try:
        fenetre = Fenetre.model_validate(document["fenetre"]) if document.get("fenetre") else None
    except ValidationError as exc:
        raise CasInvalide("fenêtre illisible") from exc
    credits = document.get("credits_estimes", 0)
    if isinstance(credits, bool) or not isinstance(credits, int) or credits < 0:
        raise CasInvalide("credits_estimes n'est pas un entier positif")
    requete = document.get("requete", "")
    if not isinstance(requete, str):
        raise CasInvalide("requete n'est pas un texte")
    brutes = document.get("videos")
    if not isinstance(brutes, list):
        raise CasInvalide("videos n'est pas une liste")
    videos: list[Video] = []
    for i, brute in enumerate(brutes):
        try:
            videos.append(
                Video.model_validate({**brute, "mode": "enregistre", "enregistre_le": enregistre_le})
            )
        except (ValidationError, TypeError) as exc:
            raise CasInvalide(f"vidéo {i} refusée : elle ne respecte pas {VIDEO_V1}") from exc
    return CasEnregistre(
        enregistre_le=enregistre_le,
        phrases=phrases,
        comptes=_liste_de_textes(document, "comptes"),
        plateformes=_liste_de_textes(document, "plateformes"),
        fenetre=fenetre,
        requete=requete,
        credits_estimes=credits,
        videos=videos,
    )


def requete_en_clair(phrases: Sequence[str], fenetre: Fenetre | None, comptes: Sequence[str]) -> str:
    """Requête envoyée à Oriane, lisible : phrases exactes dites ou écrites, niveau, fenêtre, comptes."""
    texte = (
        "phrases exactes dites ou écrites : " + ", ".join(f"« {p} »" for p in phrases) + ", niveau default"
    )
    if fenetre is not None:
        texte += f", du {fenetre.debut.date().isoformat()} au {fenetre.fin.date().isoformat()}"
    if comptes:
        texte += ", comptes " + ", ".join(comptes)
    return texte


def construire_document(
    *,
    enregistre_le: datetime,
    phrases: Sequence[str],
    comptes: Sequence[str],
    plateformes: Sequence[str],
    fenetre: Fenetre | None,
    credits_estimes: int,
    videos: Sequence[Video],
) -> dict[str, Any]:
    """Document de cas prêt à écrire ; chaque vidéo y est en mode `enregistre`."""
    if fenetre is None and videos:
        fenetre = Fenetre(debut=min(v.publie_le for v in videos), fin=max(v.publie_le for v in videos))
    document: dict[str, Any] = {
        "enregistre_le": enregistre_le.isoformat(timespec="seconds"),
        "projection": "default",
        "credits_estimes": credits_estimes,
        "phrases": list(phrases),
        "comptes": list(comptes),
        "requete": requete_en_clair(phrases, fenetre, comptes),
        "videos": [
            v.model_copy(update={"mode": "enregistre", "enregistre_le": enregistre_le}).model_dump(
                mode="json"
            )
            for v in videos
        ],
    }
    if plateformes:
        document["plateformes"] = list(plateformes)
    if fenetre is not None:
        document["fenetre"] = fenetre.model_dump(mode="json")
    return document


def ecrire_fichier(chemin: Path, document: dict[str, Any]) -> CasEnregistre:
    """Écrit le cas après l'avoir validé ; si un champ est refusé, rien n'est écrit (`CasInvalide`)."""
    cas = valider(document)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    provisoire = chemin.with_name(chemin.name + ".tmp")
    provisoire.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(provisoire, chemin)
    return cas


def lire_cas(config: Configuration) -> CasEnregistre | None:
    """Cas du fichier, ou `None` s'il n'existe pas ; `CasInvalide` s'il est illisible ou refusé."""
    chemin = fichier_cas(config)
    if not chemin.is_file():
        return None
    try:
        document = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CasInvalide("le fichier du cas est illisible") from exc
    return valider(document)


def oublier_chargement() -> None:
    """Oublie ce qui a été chargé : le prochain `charger` réécrit le cas en base (après un appel direct)."""
    _cache_chargement.clear()


def charger(config: Configuration, *, avec_videos: bool) -> CasEnregistre | None:
    """Pose le cas en base : document `cas` (phrases, requête, fenêtre) et, si demandé, ses vidéos.

    Sans fichier, rend `None`. Idempotent : le même fichier n'est pas réécrit tant qu'il ne change pas.
    En mode direct, le document `cas` ne porte pas `enregistre_le` (le radar direct n'est pas rejoué).
    """
    cas = lire_cas(config)
    if cas is None:
        return None
    chemin = fichier_cas(config)
    cle = (str(config.chemin_base), str(chemin), chemin.stat().st_mtime_ns, avec_videos)
    if cle in _cache_chargement and base.lire(TYPE_CAS, IDENTIFIANT_CAS) is not None:
        return cas
    document: dict[str, Any] = {"phrases": cas.phrases, "requete": cas.requete}
    if cas.fenetre is not None:
        document["fenetre"] = cas.fenetre.model_dump(mode="json")
    if avec_videos:
        document["enregistre_le"] = cas.enregistre_le.isoformat()
        for video in cas.videos:
            base.ecrire("video", video.identifiant, VIDEO_V1, video.model_dump(mode="json"))
    base.ecrire(TYPE_CAS, IDENTIFIANT_CAS, CAS_V1, document)
    _cache_chargement[cle] = cas.enregistre_le
    return cas
