"""Normalisation `mots.v1`, figée et versionnée : la même pour l'écart au mot, les récits et les libellés.

Règles : forme Unicode composée (NFC), minuscules, apostrophe et trait d'union changés en espace,
autre ponctuation et symboles retirés, accents gardés, nombres gardés tels que transcrits
(« dix mille » et « 10 000 » restent distincts). Toute modification de ces règles crée `mots.v2`.
"""

from __future__ import annotations

import unicodedata

NORMALISATION_MOTS_V1 = "mots.v1"

# Apostrophes et traits d'union (droits, typographiques, insécables) : changés en espace.
SEPARATEURS = frozenset("'’ʼ‘`´-‐‑‒–—―−")


def _caractere(c: str) -> str:
    """Rend le caractère gardé, une espace, ou une chaîne vide s'il est retiré."""
    if c in SEPARATEURS or c.isspace():
        return " "
    categorie = unicodedata.category(c)
    if categorie[0] in "LMN":  # lettres, signes diacritiques, chiffres
        return c
    return ""  # ponctuation, symboles, caractères de contrôle


def normaliser(texte: str) -> list[str]:
    """Découpe un texte en mots normalisés selon `mots.v1`."""
    compose = unicodedata.normalize("NFC", texte).lower()
    nettoye = "".join(_caractere(c) for c in unicodedata.normalize("NFC", compose))
    return nettoye.split()
