"""Libellés refusés : aucun mot qui qualifie une vidéo ou un récit à la place du journaliste.

Le filtre s'applique aux seuls segments `libelle` (textes écrits par le service). Il ne s'applique
jamais aux segments `citation` (propos rapportés tels quels) ni au constat écrit par le journaliste.
"""

from __future__ import annotations

import unicodedata

from app.mots import normaliser

# Six racines et leurs accords, comparés par mot entier après normalisation `mots.v1`.
LIBELLES_REFUSES = frozenset(
    {
        "faux",
        "fausse",
        "fausses",
        "premier",
        "premiers",
        "première",
        "premières",
        "original",
        "originaux",
        "originale",
        "originales",
        "manipulé",
        "manipulés",
        "manipulée",
        "manipulées",
        "coordonné",
        "coordonnés",
        "coordonnée",
        "coordonnées",
        "déformé",
        "déformés",
        "déformée",
        "déformées",
    }
)


def desaccentuer(mot: str) -> str:
    """Forme réservée au filtre : décomposition NFD, marques combinantes retirées, minuscules.

    Elle ne change pas `mots.v1` : elle sert seulement à refuser aussi « premiere » ou « DEFORME ».
    """
    decompose = unicodedata.normalize("NFD", mot)
    return "".join(c for c in decompose if not unicodedata.combining(c)).lower()


_REFUSES_DESACCENTUES = frozenset(desaccentuer(mot) for mot in LIBELLES_REFUSES)


def contient_libelle_refuse(texte: str) -> str | None:
    """Rend le premier mot refusé trouvé dans le texte (normalisé), ou `None` s'il n'y en a pas.

    La comparaison se fait sur la forme désaccentuée : accents présents ou absents, même refus.
    """
    for mot in normaliser(texte):
        if desaccentuer(mot) in _REFUSES_DESACCENTUES:
            return mot
    return None
