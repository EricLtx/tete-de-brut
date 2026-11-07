"""Libellés refusés : aucun mot qui qualifie une vidéo ou un récit à la place du journaliste.

Le filtre s'applique aux seuls segments `libelle` (textes écrits par le service). Il ne s'applique
jamais aux segments `citation` (propos rapportés tels quels) ni au constat écrit par le journaliste.
"""

from __future__ import annotations

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


def contient_libelle_refuse(texte: str) -> str | None:
    """Rend le premier mot refusé trouvé dans le texte (normalisé), ou `None` s'il n'y en a pas."""
    for mot in normaliser(texte):
        if mot in LIBELLES_REFUSES:
            return mot
    return None
