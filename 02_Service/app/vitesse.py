"""Vitesse d'un récit : vidéos publiées par jour sur deux fenêtres (48 h et 7 jours) et leur rapport.

Ce module compte et divise, il ne qualifie rien. Chaque mesure dit sa méthode et sa fenêtre ; sous
`SEUIL_ECHANTILLON` vidéos dans une fenêtre, la valeur est nulle et dit sa raison. Quand l'échantillon
est tronqué (page pleine), la méthode dit « au moins » : des vidéos plus anciennes ou plus récentes
ont pu ne pas être consultées.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.mesures import SOURCE_MESURES, echantillon_de
from app.modeles import Fenetre, Mesure, Video

SEUIL_ECHANTILLON = 3  # (H) sous ce nombre de vidéos dans une fenêtre, aucune valeur n'est donnée
RAISON_TROP_PETIT = "échantillon trop petit"


def _dans(videos: Sequence[Video], fenetre: Fenetre) -> int:
    return sum(1 for v in videos if fenetre.debut < v.publie_le <= fenetre.fin)


def _mesure_par_jour(
    nom: str, videos: Sequence[Video], calcule_le: datetime, jours: int, libelle: str
) -> Mesure:
    fenetre = Fenetre(debut=calcule_le - timedelta(days=jours), fin=calcule_le)
    echantillon = echantillon_de(videos)
    nombre = _dans(videos, fenetre)
    assez = nombre >= SEUIL_ECHANTILLON
    methode = (
        f"nombre de vidéos publiées dans les {libelle} avant le calcul, divisé par {jours} jours ; "
        f"{nombre} vidéos dans cette fenêtre"
    )
    if echantillon.tronque:
        methode += " ; échantillon tronqué : au moins cette valeur"
    return Mesure(
        nom=nom,
        valeur=round(nombre / jours, 2) if assez else None,
        unite="vidéos par jour",
        methode=methode if assez else f"{methode} ; sous {SEUIL_ECHANTILLON} vidéos, aucune valeur",
        fenetre=fenetre,
        echantillon=echantillon,
        source=SOURCE_MESURES,
        raison=None if assez else f"{RAISON_TROP_PETIT} ({nombre} vidéo(s) dans la fenêtre)",
    )


def mesures_de_vitesse(videos: Sequence[Video], calcule_le: datetime) -> list[Mesure]:
    """Trois mesures : vidéos par jour sur 48 h, sur 7 jours, et le rapport des deux."""
    court = _mesure_par_jour("vitesse_48h", videos, calcule_le, 2, "48 heures")
    long = _mesure_par_jour("vitesse_7j", videos, calcule_le, 7, "7 jours")
    echantillon = echantillon_de(videos)
    fenetre = Fenetre(debut=long.fenetre.debut, fin=calcule_le)
    calculable = court.valeur is not None and long.valeur is not None and long.valeur > 0
    methode = (
        "vidéos par jour sur 48 heures divisées par vidéos par jour sur 7 jours, mêmes vidéos consultées"
    )
    if echantillon.tronque:
        methode += " ; échantillon tronqué : au moins ce nombre de vidéos par fenêtre, rapport indicatif"
    rapport = Mesure(
        nom="vitesse",
        valeur=round(court.valeur / long.valeur, 2) if calculable else None,  # type: ignore[operator]
        unite="rapport (sans unité)",
        methode=methode,
        fenetre=fenetre,
        echantillon=echantillon,
        source=SOURCE_MESURES,
        raison=None if calculable else f"{RAISON_TROP_PETIT} sur l'une des deux fenêtres (48 h ou 7 jours)",
    )
    return [court, long, rapport]
