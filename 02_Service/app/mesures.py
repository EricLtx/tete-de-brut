"""Mesures de volume d'un récit : vidéos trouvées, comptes distincts, vues cumulées « selon Oriane ».

Chaque mesure dit sa méthode, sa fenêtre, son échantillon et sa source. Ce module ne qualifie rien :
il compte. Une valeur nulle dit sa raison.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modeles import SOURCE_ORIANE, Echantillon, Fenetre, Mesure, Video

LIMITE_PAGE = 100
SOURCE_MESURES = f"{SOURCE_ORIANE} (niveau default), vidéos consultées"


def echantillon_de(videos: Sequence[Video]) -> Echantillon:
    """Résultats consultés, page de 100, tronqué si la page est pleine."""
    return Echantillon(
        resultats_consultes=len(videos), limite_page=LIMITE_PAGE, tronque=len(videos) >= LIMITE_PAGE
    )


def mesures_de_volume(videos: Sequence[Video], fenetre: Fenetre) -> list[Mesure]:
    """Les trois mesures de volume d'un récit, sur la fenêtre de la requête."""
    echantillon = echantillon_de(videos)
    vues = [v.vues_selon_oriane for v in videos if v.vues_selon_oriane is not None]
    return [
        Mesure(
            nom="videos_trouvees",
            valeur=len(videos),
            unite="vidéos",
            methode="nombre de vidéos rendues par la requête, chaque vidéo comptée une fois",
            fenetre=fenetre,
            echantillon=echantillon,
            source=SOURCE_MESURES,
        ),
        Mesure(
            nom="comptes_distincts",
            valeur=len({(v.plateforme, v.compte) for v in videos}),
            unite="comptes",
            methode="nombre de comptes distincts (plateforme et compte) parmi les vidéos rendues",
            fenetre=fenetre,
            echantillon=echantillon,
            source=SOURCE_MESURES,
        ),
        Mesure(
            nom="vues_cumulees",
            valeur=sum(vues) if vues else None,
            unite="vues selon Oriane",
            methode="somme des vues annoncées par Oriane pour les vidéos rendues, non vérifiées",
            fenetre=fenetre,
            echantillon=echantillon,
            source=SOURCE_MESURES,
            raison=None if vues else "aucune vue fournie par Oriane pour ces vidéos",
        ),
    ]
