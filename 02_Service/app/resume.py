"""Résumé de la fiche par gabarit déterministe (S08) : point d'entrée unique `resumer(comparaison)`.

Le gabarit v1 n'écrit que des phrases fixes (segments `libelle`, passés au filtre des libellés
refusés) et rapporte les mots qui diffèrent en extraits (segments `citation`, jamais filtrés,
40 mots au plus). Il décrit ce qui diffère, jamais ce que cela veut dire : le constat et la
décision reviennent au journaliste.

S10 (ADR-0002) : avec `RESUME_MODE=modele` et `MODELE_LANGUE_API_KEY`, `resumer` demande le résumé
à un modèle de langue (`app/modele_langue.py`), n'envoie que les extraits `citation`, passe la
sortie au filtre des libellés refusés et la marque « rédigé par un modèle de langue, à relire ».
Échec, refus ou libellé refusé : le gabarit v1 est servi et une ligne part au journal. Sans
configuration, le gabarit seul, comme en S08. La fiche enregistre le résumé : il n'est pas
recalculé à chaque lecture.
"""

from __future__ import annotations

import logging
import re
import time

from app import base, modele_langue
from app.config import Configuration, ErreurConfiguration
from app.libelles import contient_libelle_refuse
from app.modele_langue import ErreurModele, ExtraitModele
from app.modeles import METHODE_GABARIT_V1, Ecart, Operation, Resume, Segment
from app.mots import normaliser

journal = logging.getLogger("tete_de_brut")

LIMITE_MOTS_EXTRAIT = 40

# Les trois listes de `ecart.v1`, dans l'ordre de lecture, avec leur nom affiché.
CANAUX: tuple[tuple[str, str], ...] = (
    ("operations", "Parole"),
    ("ecart_legende", "Légende"),
    ("ecart_texte_ecran", "Texte à l'écran"),
)


def extrait(mots: list[str] | str, limite: int = LIMITE_MOTS_EXTRAIT) -> str:
    """Extrait d'au plus `limite` mots, terminé par « … » s'il a été coupé."""
    liste = mots.split() if isinstance(mots, str) else list(mots)
    if len(liste) <= limite:
        return " ".join(liste)
    return " ".join(liste[:limite]) + " …"


def libelle(texte: str) -> Segment:
    """Phrase fixe du gabarit (filtrée par le modèle `Segment`)."""
    return Segment(type="libelle", texte=texte)


def citation(mots: list[str] | str) -> Segment:
    """Mots rapportés tels que lus chez Oriane (normalisés `mots.v1`), en extrait."""
    return Segment(type="citation", texte=extrait(mots))


def compter(operations: list[Operation]) -> tuple[int, int, int]:
    """Mots retirés, ajoutés et remplacés (comptés côté source) dans une liste d'opérations."""
    retires = sum(len(o.mots_source) for o in operations if o.type == "retire")
    ajoutes = sum(len(o.mots_reprise) for o in operations if o.type == "ajoute")
    remplaces = sum(len(o.mots_source) for o in operations if o.type == "remplace")
    return retires, ajoutes, remplaces


def decrire_operation(canal: str, operation: Operation) -> list[Segment]:
    """Un indice de transformation : une phrase fixe, puis le ou les extraits concernés."""
    rang_source = operation.position_source + 1
    rang_reprise = operation.position_reprise + 1
    if operation.type == "retire":
        return [
            libelle(
                f"{canal}, selon Oriane : mots de la source absents de la reprise, "
                f"à partir du mot {rang_source} de la source."
            ),
            citation(operation.mots_source),
        ]
    if operation.type == "ajoute":
        return [
            libelle(
                f"{canal}, selon Oriane : mots de la reprise absents de la source, "
                f"à partir du mot {rang_reprise} de la reprise."
            ),
            citation(operation.mots_reprise),
        ]
    return [
        libelle(
            f"{canal}, selon Oriane : mots de la source remplacés dans la reprise, "
            f"à partir du mot {rang_source} de la source ; dans la source :"
        ),
        citation(operation.mots_source),
        libelle("dans la reprise :"),
        citation(operation.mots_reprise),
    ]


def indices_de_transformation(comparaison: Ecart) -> list[Segment]:
    """Tous les indices de transformation de la comparaison, canal par canal, dans l'ordre."""
    segments: list[Segment] = []
    for champ, canal in CANAUX:
        for operation in getattr(comparaison, champ):
            segments.extend(decrire_operation(canal, operation))
    if not segments:
        segments.append(
            libelle(
                "Aucun écart au mot relevé entre les deux versions "
                "(parole, légende, texte à l'écran), selon Oriane."
            )
        )
    return segments


def resumer_par_gabarit(comparaison: Ecart) -> Resume:
    """Résumé `gabarit v1` d'une comparaison : décompte par canal et écart rencontré d'abord."""
    segments = [
        libelle(
            "Deux versions comparées au mot (normalisation mots.v1), d'après les transcriptions, "
            "légendes et textes à l'écran lus chez Oriane."
        )
    ]
    for champ, canal in CANAUX:
        operations: list[Operation] = getattr(comparaison, champ)
        retires, ajoutes, remplaces = compter(operations)
        segments.append(
            libelle(
                f"{canal}, selon Oriane : mots retirés : {retires} ; ajoutés : {ajoutes} ; "
                f"remplacés : {remplaces}."
            )
        )
        if operations:
            premiere_operation = operations[0]
            mots = premiere_operation.mots_source or premiere_operation.mots_reprise
            segments.append(libelle(f"{canal}, écart rencontré d'abord :"))
            segments.append(citation(mots))
    segments.append(libelle("Le constat et la décision reviennent au journaliste."))
    return Resume(segments=segments, methode=METHODE_GABARIT_V1)


# --- S10 : résumé rédigé par un modèle de langue, toujours filtré, gabarit en repli ---------------

ROUTE_JOURNAL_MODELE = "resume.modele"
METHODE_MODELE = "rédigé par un modèle de langue ({modele}), à relire"
LIMITE_PHRASES_MODELE = 4
# Valeurs de décision (`decision.v1`) qu'un résumé du modèle ne doit jamais écrire.
DECISIONS_INTERDITES = (("ne", "pas", "amplifier"), ("prêt", "à", "traiter"))
_FIN_DE_PHRASE = re.compile(r"[.!?…]+(?:\s|$)")


def extraits_pour_modele(comparaison: Ecart) -> list[ExtraitModele]:
    """Les seuls extraits `citation` de la comparaison (40 mots au plus), avec leur contexte fixe."""
    extraits: list[ExtraitModele] = []
    for champ, canal in CANAUX:
        for operation in getattr(comparaison, champ):
            for version, mots in (("source", operation.mots_source), ("reprise", operation.mots_reprise)):
                if mots:
                    texte = citation(mots).texte
                    extraits.append(ExtraitModele(canal, version, operation.type, texte))
    return extraits


def _configuration() -> Configuration | None:
    """Réglages du modèle lus dans l'environnement au moment du résumé ; invalides, aucun modèle."""
    try:
        return Configuration.depuis_environnement()
    except ErreurConfiguration as exc:
        journal.warning("résumé par modèle ignoré : %s", exc)
        return None


def _raison_de_refus(texte: str) -> str | None:
    """Pourquoi un texte du modèle ne peut pas être servi, ou `None` s'il passe le filtre."""
    if contient_libelle_refuse(texte) is not None:
        return "résumé du modèle refusé : libellé"
    mots = normaliser(texte)
    for interdite in DECISIONS_INTERDITES:
        n = len(interdite)
        if any(tuple(mots[i : i + n]) == interdite for i in range(len(mots) - n + 1)):
            return "résumé du modèle refusé : décision"
    if len(_FIN_DE_PHRASE.findall(texte.strip())) > LIMITE_PHRASES_MODELE:
        return "résumé du modèle refusé : plus de quatre phrases"
    return None


def _consigner_modele(cible: str, config: Configuration, debut: float, code: int | None) -> None:
    """Ligne au journal des appels : raison en clair, modèle, code et durée ; jamais la réponse ni la clé."""
    base.consigner(
        route=ROUTE_JOURNAL_MODELE,
        cible=cible,
        resultats={"modele": config.modele_langue_id},
        duree_ms=round((time.monotonic() - debut) * 1000, 1),
        code=code,
    )


def resumer(comparaison: Ecart) -> Resume:
    """Résumé de la fiche : par le modèle si configuré et accepté par le filtre, sinon gabarit v1."""
    gabarit = resumer_par_gabarit(comparaison)
    config = _configuration()
    if config is None or config.resume_mode != "modele" or not config.modele_langue_cle:
        return gabarit
    extraits = extraits_pour_modele(comparaison)
    if not extraits:
        return gabarit  # aucun écart au mot : rien à rédiger, le gabarit le dit déjà
    debut = time.monotonic()
    try:
        texte = modele_langue.rediger(extraits, config=config)
    except ErreurModele as exc:
        _consigner_modele(exc.raison, config, debut, exc.code)
        return gabarit
    raison = _raison_de_refus(texte)
    if raison is not None:
        _consigner_modele(raison, config, debut, 200)
        return gabarit
    _consigner_modele("résumé du modèle accepté", config, debut, 200)
    return Resume(
        segments=[
            libelle(
                "Résumé rédigé par un modèle de langue, à relire, d'après les extraits lus chez Oriane :"
            ),
            libelle(texte),
            libelle("Le constat et la décision reviennent au journaliste."),
        ],
        methode=METHODE_MODELE.format(modele=config.modele_langue_id),
    )
