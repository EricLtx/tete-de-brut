"""Résumé de la fiche par gabarit déterministe (S08) : point d'entrée unique `resumer(comparaison)`.

Le gabarit v1 n'écrit que des phrases fixes (segments `libelle`, passés au filtre des libellés
refusés) et rapporte les mots qui diffèrent en extraits (segments `citation`, jamais filtrés,
40 mots au plus). Il décrit ce qui diffère, jamais ce que cela veut dire : le constat et la
décision reviennent au journaliste. S10 pourra aiguiller ici vers un résumé rédigé par un modèle
de langue (`RESUME_MODE=modele`) sans changer la signature.
"""

from __future__ import annotations

from app.modeles import METHODE_GABARIT_V1, Ecart, Operation, Resume, Segment

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


def resumer(comparaison: Ecart) -> Resume:
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
