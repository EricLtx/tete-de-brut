"""Écart au mot entre deux textes, sur la normalisation `mots.v1` (S07).

Distance d'édition par programmation dynamique, en Python standard. Le résultat est une liste
d'opérations `retire`, `ajoute` ou `remplace` avec leurs positions (dès 0) dans la source et dans
la reprise. Le module ne qualifie rien : il décrit ce qui diffère, jamais ce que cela veut dire.
"""

from __future__ import annotations

import hashlib

from app.modeles import (
    AttributionTranscription,
    Ecart,
    HeureDansLaVideo,
    Operation,
    TranscriptionsComparees,
    Video,
)
from app.mots import NORMALISATION_MOTS_V1, normaliser

TYPE_DOCUMENT = "ecart"


def identifiant_comparaison(video_source: str, video_reprise: str) -> str:
    """Identifiant stable dérivé du couple, dans l'ordre source puis reprise."""
    empreinte = hashlib.sha256(f"{video_source}\n{video_reprise}".encode()).hexdigest()
    return f"cmp-{empreinte[:12]}"


def _alignement(source: list[str], reprise: list[str]) -> list[tuple[str, int, int]]:
    """Alignement de coût minimal : étapes (`=`, `s`, `d`, `i`) avec l'indice concerné de chaque côté."""
    n, m = len(source), len(reprise)
    precedente = list(range(m + 1))
    lignes = [precedente]
    for i in range(1, n + 1):
        courante = [i] + [0] * m
        mot = source[i - 1]
        for j in range(1, m + 1):
            if mot == reprise[j - 1]:
                courante[j] = precedente[j - 1]
            else:
                courante[j] = 1 + min(precedente[j - 1], precedente[j], courante[j - 1])
        lignes.append(courante)
        precedente = courante
    etapes: list[tuple[str, int, int]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and source[i - 1] == reprise[j - 1] and lignes[i][j] == lignes[i - 1][j - 1]:
            etapes.append(("=", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and lignes[i][j] == lignes[i - 1][j - 1] + 1:
            etapes.append(("s", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and lignes[i][j] == lignes[i - 1][j] + 1:
            etapes.append(("d", i - 1, j))
            i -= 1
        else:
            etapes.append(("i", i, j - 1))
            j -= 1
    etapes.reverse()
    return etapes


def comparer_mots(source: list[str], reprise: list[str]) -> list[Operation]:
    """Opérations au mot qui font passer de la source à la reprise (un bloc d'écarts = une opération)."""
    operations: list[Operation] = []
    bloc_source: list[str] = []
    bloc_reprise: list[str] = []
    debut = (0, 0)

    def clore() -> None:
        if not bloc_source and not bloc_reprise:
            return
        genre = "remplace" if bloc_source and bloc_reprise else ("retire" if bloc_source else "ajoute")
        operations.append(
            Operation(
                type=genre,
                position_source=debut[0],
                position_reprise=debut[1],
                mots_source=list(bloc_source),
                mots_reprise=list(bloc_reprise),
            )
        )
        bloc_source.clear()
        bloc_reprise.clear()

    pos_s = pos_r = 0
    for genre, i, j in _alignement(source, reprise):
        if genre == "=":
            clore()
            pos_s, pos_r = i + 1, j + 1
            continue
        if not bloc_source and not bloc_reprise:
            debut = (pos_s, pos_r)
        if genre in ("s", "d"):
            bloc_source.append(source[i])
            pos_s = i + 1
        if genre in ("s", "i"):
            bloc_reprise.append(reprise[j])
            pos_r = j + 1
    clore()
    return operations


def comparer_textes(texte_source: str, texte_reprise: str) -> list[Operation]:
    """Écart au mot entre deux textes bruts, après normalisation `mots.v1`."""
    return comparer_mots(normaliser(texte_source), normaliser(texte_reprise))


def calculer_ecart(source: Video, reprise: Video, *, mode: str, enregistre_le: str | None) -> Ecart:
    """Écart `ecart.v1` entre deux vidéos : parole, légende et texte à l'écran, même traitement."""
    return Ecart.model_validate(
        {
            "mode": mode,
            "enregistre_le": enregistre_le,
            "identifiant": identifiant_comparaison(source.identifiant, reprise.identifiant),
            "video_source": source.identifiant,
            "video_reprise": reprise.identifiant,
            "operations": comparer_textes(source.transcription.texte, reprise.transcription.texte),
            "ecart_legende": comparer_textes(source.legende, reprise.legende),
            "ecart_texte_ecran": comparer_textes(source.texte_ecran.texte, reprise.texte_ecran.texte),
            "normalisation": NORMALISATION_MOTS_V1,
            "transcriptions": TranscriptionsComparees(
                source=AttributionTranscription(lue_le=source.transcription.lue_le),
                reprise=AttributionTranscription(lue_le=reprise.transcription.lue_le),
            ),
            "heure_dans_la_video": HeureDansLaVideo(),
        }
    )
