"""Normalisation `mots.v1`, figée et versionnée : la même pour l'écart au mot, les récits et les libellés.

Règles : forme Unicode composée (NFC), minuscules, apostrophe et trait d'union changés en espace,
autre ponctuation et symboles retirés sauf la virgule ou le point placé entre deux chiffres
(séparateur décimal : « 3,5 » et « 3.5 » restent un seul mot), accents gardés, nombres gardés tels
que transcrits (« dix mille » et « 10 000 » restent distincts), découpage sur les espaces.
Toute modification de ces règles crée `mots.v2`.
"""

from __future__ import annotations

import unicodedata

NORMALISATION_MOTS_V1 = "mots.v1"

# Apostrophes et traits d'union (droits, typographiques, insécables) : changés en espace.
SEPARATEURS = frozenset("'’ʼ‘`´-‐‑‒–—―−")


SEPARATEURS_DECIMAUX = frozenset(",.")


def _est_chiffre(c: str) -> bool:
    return unicodedata.category(c) == "Nd"


def _caractere(texte: str, i: int) -> str:
    """Rend le caractère `texte[i]` gardé, une espace, ou une chaîne vide s'il est retiré."""
    c = texte[i]
    if c in SEPARATEURS or c.isspace():
        return " "
    if c in SEPARATEURS_DECIMAUX and 0 < i < len(texte) - 1:
        if _est_chiffre(texte[i - 1]) and _est_chiffre(texte[i + 1]):
            return c  # séparateur décimal entre deux chiffres : le nombre reste tel que transcrit
    categorie = unicodedata.category(c)
    if categorie[0] in "LMN":  # lettres, signes diacritiques, chiffres
        return c
    return ""  # ponctuation, symboles, caractères de contrôle


def normaliser(texte: str) -> list[str]:
    """Découpe un texte en mots normalisés selon `mots.v1`."""
    compose = unicodedata.normalize("NFC", texte).lower()
    nettoye = "".join(_caractere(compose, i) for i in range(len(compose)))
    return nettoye.split()
