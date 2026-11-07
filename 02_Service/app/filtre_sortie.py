"""Filtre propre à la sortie du modèle de langue (S10, ADR-0002), plus large que `app/libelles.py`.

Le gabarit n'écrit que des phrases fixes ; le modèle écrit un texte libre, où la qualification peut
passer par un synonyme (« trompeuse », « truquée »). Ce filtre refuse donc les six racines, les termes de
même sens et quelques tournures, après mise en minuscules et désaccentuation. Un faux positif ne coûte
qu'un repli sur le gabarit. `app/libelles.py` et le contrat ne changent pas.
"""

from __future__ import annotations

import re

from app.libelles import desaccentuer

# Préfixes désaccentués : un mot qui commence par l'un d'eux est refusé (accords et noms dérivés compris).
PREFIXES_REFUSES = (
    "faux",
    "fauss",
    "premier",
    "origina",
    "manipul",
    "coordonn",
    "coordin",
    "deform",
    "tromp",
    "truqu",
    "falsifi",
    "mensong",
    "detourn",
    "altere",
    "fabriqu",
    "invente",
    "desinform",
    "intox",
    "fake",
    "propagand",
    "contexte",
)
# Tournures refusées, comparées sur le texte réduit à des mots désaccentués séparés par une espace.
TOURNURES_REFUSEES = (
    "sorti de son contexte",
    "cherche a faire croire",
    "change donc le sens",
    "change le sens",
)
# Valeurs de décision (`decision.v1`), sous toutes leurs formes ; `amplifi` couvre amplifier et amplifiez.
DECISIONS_REFUSEES = ("pret a traiter", "prete a traiter", "a verifier")
PREFIXES_DECISION = ("amplifi",)


def mots_reduits(texte: str) -> list[str]:
    """Mots en minuscules sans accents ; tout ce qui n'est pas lettre ou chiffre (`_` compris) sépare."""
    return [m for m in re.split(r"[^a-z0-9]+", desaccentuer(texte)) if m]


def motif_libelle(texte: str) -> str | None:
    """Le premier mot ou la première tournure de qualification trouvé, ou `None`."""
    mots = mots_reduits(texte)
    for mot in mots:
        if mot.startswith(PREFIXES_REFUSES):
            return mot
    plat = f" {' '.join(mots)} "
    for tournure in TOURNURES_REFUSEES:
        if f" {tournure} " in plat:
            return tournure
    return None


def motif_decision(texte: str) -> str | None:
    """La première valeur de décision trouvée (accents, casse, `ne_pas_amplifier` indifférents), ou `None`."""
    mots = mots_reduits(texte)
    for mot in mots:
        if mot.startswith(PREFIXES_DECISION):
            return mot
    plat = f" {' '.join(mots)} "
    for decision in DECISIONS_REFUSEES:
        if f" {decision} " in plat:
            return decision
    return None
