"""Liste blanche : seuls ces champs d'Oriane entrent dans `video.v1`, tout le reste est ignoré.

C'est le seul fichier (avec `app/oriane.py`, qui y puise) où vivent les noms de champs d'Oriane.
La projection lit chaque champ autorisé par son nom : elle ne parcourt jamais la réponse, donc un
champ de tiers servi par Oriane ne peut ni entrer dans la vidéo ni être recopié ailleurs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.modeles import Video

# --- table de correspondance : nom Oriane -> champ français de `video.v1` -------------------------

CORRESPONDANCE: dict[str, str] = {
    "id": "identifiant",  # identifiant du contenu chez Oriane
    "platform": "plateforme",  # tiktok, instagram ou youtube
    "platformId": "identifiant_plateforme",  # identifiant de la vidéo sur la plateforme
    "profileHandle": "compte",  # identifiant public du compte (pas le nom affiché)
    "publishedAt": "publie_le",  # date de publication
    "viewsCount": "vues_selon_oriane",  # vues, telles que les compte Oriane
    "interactionsCount": "interactions_selon_oriane",  # interactions, telles que les compte Oriane
    "caption": "legende",  # légende du contenu
    "matchedQueries": "requetes_trouvees",  # requêtes de la recherche qui ont trouvé le contenu
    "media[].transcript": "transcription.texte",  # parole transcrite par Oriane (niveau default)
    "media[].onScreenText": "texte_ecran.texte",  # liste de chaînes, jointe par des retours à la ligne
}

# Noms utilisés pour construire la requête (filtres de la recherche).
CHEMIN_RECHERCHE = "/rest/contents/search"
FILTRE_TRANSCRIPTION = "transcript"  # parole transcrite
FILTRE_TEXTE_ECRAN = "onScreenText"  # texte affiché à l'écran
FILTRE_COMPTE = "profileHandle"  # identifiant public du compte
FILTRE_DATE = "publishedAt"  # fenêtre de publication {after, before}
FILTRE_PLATEFORME = "platform"  # {"includes": [...]}, relevé H01 (pas exactMatch)
OPERATEUR_PHRASES = "includesExactly"  # la phrase doit apparaître telle quelle
OPERATEUR_COMPTES = "exactMatch"  # le compte doit être exactement celui-là
OPERATEUR_PLATEFORMES = "includes"  # la plateforme est l'une de celles-là

# Champs servis par Oriane qui ne doivent jamais entrer dans le service (jamais écrits, jamais journalisés).
# La projection ne les lit pas ; cette liste sert aux tests et aux contrôles d'autres modules.
CHAMPS_REFUSES = frozenset(
    {
        "profileDisplayName",
        "profilePictureUrl",
        "thumbnailMediaUrl",
        "thumbnailMediaId",
        "mentions",
        "hashtags",
        "coAuthors",
        "audioAuthor",
        "popularComments",
        "profileBio",
        "locationPlatformId",
        "locationCompleteAddress",
        "locationLatitude",
        "locationLongitude",
        "profileLocationPlatformId",
        "profileLocationCompleteAddress",
        "profileLocationLatitude",
        "profileLocationLongitude",
    }
)
CHAMPS_REFUSES_MEDIA = frozenset({"tags", "frames", "transcriptChunks"})
PREFIXES_REFUSES = (
    "coAuthors",
    "audio",
    "location",
    "profileLocation",
    "profileFollowers",
    "profileFollowing",
)


class ResultatIllisible(ValueError):
    """Un résultat d'Oriane ne porte pas ce que `video.v1` exige : il est écarté, pas deviné."""


def lien_video(plateforme: str, compte: str, identifiant_plateforme: str) -> str:
    """Lien public reconstruit (format à vérifier par H03) ; jamais lu dans la réponse d'Oriane."""
    if plateforme == "tiktok":
        return f"https://www.tiktok.com/@{compte}/video/{identifiant_plateforme}"
    if plateforme == "instagram":
        return f"https://www.instagram.com/reel/{identifiant_plateforme}/"
    if plateforme == "youtube":
        return f"https://www.youtube.com/watch?v={identifiant_plateforme}"
    raise ResultatIllisible(f"plateforme non prise en charge : {plateforme}")


def _texte(valeur: Any) -> str:
    return valeur.strip() if isinstance(valeur, str) else ""


def _compte(valeur: Any) -> int | None:
    if isinstance(valeur, bool) or not isinstance(valeur, int | float) or valeur < 0:
        return None
    return int(valeur)


def _media(resultat: dict[str, Any]) -> list[dict[str, Any]]:
    media = resultat.get("media")
    return [m for m in media if isinstance(m, dict)] if isinstance(media, list) else []


def _transcription(resultat: dict[str, Any]) -> str:
    return "\n".join(t for m in _media(resultat) if (t := _texte(m.get("transcript"))))


def _texte_ecran(resultat: dict[str, Any]) -> str:
    morceaux: list[str] = []
    for m in _media(resultat):
        brut = m.get("onScreenText")
        if isinstance(brut, str):
            brut = [brut]
        if isinstance(brut, list):
            morceaux.extend(t for t in (_texte(x) for x in brut) if t)
    return "\n".join(morceaux)


def projeter(resultat: dict[str, Any], *, lue_le: datetime | None = None) -> Video:
    """Projette un résultat d'Oriane (niveau `default`) vers `video.v1`, en mode direct.

    Lève `ResultatIllisible` si un champ obligatoire manque ou si la plateforme est inconnue.
    """
    lue_le = lue_le or datetime.now(UTC)
    identifiant = _texte(resultat.get("id"))
    plateforme = _texte(resultat.get("platform")).lower()
    identifiant_plateforme = _texte(resultat.get("platformId"))
    compte = _texte(resultat.get("profileHandle"))
    publie_le = _texte(resultat.get("publishedAt"))
    if not (identifiant and identifiant_plateforme and compte and publie_le):
        raise ResultatIllisible("identifiant, plateforme, compte ou date de publication manquant")
    requetes = resultat.get("matchedQueries")
    donnees: dict[str, Any] = {
        "identifiant": identifiant,
        "plateforme": plateforme,
        "identifiant_plateforme": identifiant_plateforme,
        "compte": compte,
        "publie_le": publie_le,
        "vues_selon_oriane": _compte(resultat.get("viewsCount")),
        "interactions_selon_oriane": _compte(resultat.get("interactionsCount")),
        "legende": _texte(resultat.get("caption")),
        "requetes_trouvees": [q for q in requetes if isinstance(q, str)]
        if isinstance(requetes, list)
        else [],
        "transcription": {
            "texte": _transcription(resultat),
            "source": "Oriane",
            "niveau": "default",
            "lue_le": lue_le,
        },
        "texte_ecran": {"texte": _texte_ecran(resultat), "source": "Oriane", "lue_le": lue_le},
        "lien": lien_video(plateforme, compte, identifiant_plateforme),
        "mode": "direct",
        "enregistre_le": None,
    }
    try:
        return Video.model_validate(donnees)
    except (
        ValueError
    ) as exc:  # la validation pydantic hérite de ValueError ; son détail peut citer des valeurs
        raise ResultatIllisible("résultat non conforme à video.v1") from exc
