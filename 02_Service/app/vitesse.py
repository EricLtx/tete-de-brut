"""Vitesse d'un récit : vidéos publiées par jour sur deux fenêtres (48 h et 7 jours) et leur rapport.

Ce module compte et divise, il ne qualifie rien. Chaque mesure dit sa méthode et sa fenêtre ; sous
`SEUIL_ECHANTILLON` vidéos dans une fenêtre, la valeur est nulle et dit sa raison. Quand l'échantillon
est tronqué (page pleine), la méthode dit « au moins » : des vidéos plus anciennes ou plus récentes
ont pu ne pas être consultées.

Les fenêtres sont ancrées sur la vidéo la plus récente retrouvée (plafonnée à la date du calcul) et non
sur le jour du calcul : un index qui date de quelques semaines donne des mesures, et la méthode dit la
référence. Sans vidéo, la référence est la date du calcul.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from app.mesures import SOURCE_MESURES, echantillon_de
from app.modeles import Fenetre, Mesure, Video

SEUIL_ECHANTILLON = 3  # (H) sous ce nombre de vidéos dans une fenêtre, aucune valeur n'est donnée
RAISON_TROP_PETIT = "échantillon trop petit"


def _dans(videos: Sequence[Video], fenetre: Fenetre) -> int:
    return sum(1 for v in videos if fenetre.debut < v.publie_le <= fenetre.fin)


def _reference(videos: Sequence[Video], calcule_le: datetime) -> datetime:
    """Publication de la vidéo la plus récente, plafonnée à `calcule_le` ; `calcule_le` sans vidéo."""
    if not videos:
        return calcule_le
    return min(max(v.publie_le for v in videos), calcule_le)


def _dit_reference(videos: Sequence[Video], reference: datetime) -> str:
    if not videos:
        return "avant le calcul"
    instant = reference.astimezone(UTC)
    return (
        f"avant la vidéo la plus récente retrouvée (le {instant:%d/%m/%Y} à "
        f"{instant.hour} h {instant.minute:02d} UTC)"
    )


def _mesure_par_jour(
    nom: str, videos: Sequence[Video], reference: datetime, jours: int, libelle: str
) -> Mesure:
    fenetre = Fenetre(debut=reference - timedelta(days=jours), fin=reference)
    echantillon = echantillon_de(videos)
    nombre = _dans(videos, fenetre)
    assez = nombre >= SEUIL_ECHANTILLON
    methode = (
        f"nombre de vidéos publiées dans les {libelle} {_dit_reference(videos, reference)}, "
        f"divisé par {jours} jours ; {nombre} vidéos dans cette fenêtre"
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
    reference = _reference(videos, calcule_le)
    court = _mesure_par_jour("vitesse_48h", videos, reference, 2, "48 heures")
    long = _mesure_par_jour("vitesse_7j", videos, reference, 7, "7 jours")
    echantillon = echantillon_de(videos)
    fenetre = Fenetre(debut=long.fenetre.debut, fin=reference)
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
