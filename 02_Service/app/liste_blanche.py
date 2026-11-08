"""Liste blanche : seuls ces champs d'Oriane entrent dans `video.v1`, tout le reste est ignoré.

C'est le seul fichier (avec `app/oriane.py`, qui y puise) où vivent les noms de champs d'Oriane.
La projection lit chaque champ autorisé par son nom : elle ne parcourt jamais la réponse, donc un
champ de tiers servi par Oriane ne peut ni entrer dans la vidéo ni être recopié ailleurs.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.modeles import LIMITE_IMAGES_CLES, Video

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
    "matchedQueries": "requetes_trouvees",  # noms `dit:`, `ecrit:` et `mots:`, ramenés aux phrases et noyaux
    "media[].transcript": "transcription.texte",  # parole transcrite par Oriane (niveau default)
    "media[].onScreenText": "texte_ecran.texte",  # liste de chaînes, jointe par des retours à la ligne
    "thumbnailMediaUrl": "apercu.vignette",  # adresse de la vignette, relayée telle que servie
    "media[].frames[].url": "apercu.images_cles",  # images clés, dix adresses au plus, telles que servies
}

# Noms utilisés pour construire la requête (filtres de la recherche).
CHEMIN_RECHERCHE = "/rest/contents/search"
FILTRE_TRANSCRIPTION = "transcript"  # parole transcrite
FILTRE_TEXTE_ECRAN = "onScreenText"  # texte affiché à l'écran
FILTRE_COMPTE = "profileHandle"  # identifiant public du compte
FILTRE_DATE = "publishedAt"  # fenêtre de publication {after, before}
FILTRE_PLATEFORME = "platform"  # {"includes": [...]}, relevé H01 (pas exactMatch)
# Lien d'une vidéo (S13, vérifié en réel le 07/11/2026 sur un lien TikTok et un lien Instagram, F018) :
# `"platformId": {"includes": [{"platform": "tiktok", "platformId": "<identifiant>"}]}`, avec en plus
# `"platform": {"includes": ["tiktok"]}`, sans phrase ni fenêtre ; Oriane rend la vidéo (totalCount 1).
FILTRE_IDENTIFIANT = "platformId"
REQUETE_DIT = "dit"  # préfixe des sous-requêtes sur la parole transcrite : « dit:<phrase> »
REQUETE_ECRIT = "ecrit"  # préfixe des sous-requêtes sur le texte à l'écran : « ecrit:<phrase> »
REQUETE_MOTS = "mots"  # préfixe des sous-requêtes d'un noyau de mots (parole et écran) : « mots:<noyau> »
LONGUEUR_MAX_PHRASE = 256
REQUETE_DIT_OU_ECRIT = "dit_ou_ecrit"  # union des deux
OPERATEUR_PHRASES = "includesExactly"  # la phrase doit apparaître telle quelle
# Couverture (F020) : tous les mots du noyau, dans n'importe quel ordre, mots partiels compris. Citation de la
# spécification OpenAPI d'Oriane (`SearchContentsRequest.Filters.Body`, champs `transcript`, `onScreenText`,
# `caption`) : « Requires matches of all words in any order, including partial words, inside the field. »
# Forme envoyée : `{"includesFuzzy": {"values": ["<noyau>"], "operator": "or"}}`.
OPERATEUR_MOTS = "includesFuzzy"
OPERATEUR_COMPTES = "exactMatch"  # le compte doit être exactement celui-là
OPERATEUR_PLATEFORMES = "includes"  # la plateforme est l'une de celles-là
OPERATEUR_COMPTES_EXCLUS = (
    "excludesExactly"  # le compte n'est aucun de ceux-là : {"values", "operator"} (S13)
)
OPERATEUR_IDENTIFIANTS = "includes"  # l'identifiant est l'un de ces couples plateforme et identifiant (S13)

# Champs servis par Oriane qui ne doivent jamais entrer dans le service (jamais écrits, jamais journalisés).
# La projection ne les lit pas ; cette liste sert aux tests et aux contrôles d'autres modules.
CHAMPS_REFUSES = frozenset(
    {
        "profileDisplayName",
        "profilePictureUrl",
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
CHAMPS_REFUSES_MEDIA = frozenset({"tags", "transcriptChunks"})
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


def _adresse(valeur: Any) -> str | None:
    """Adresse https servie par Oriane, telle quelle ; tout le reste est écarté, rien n'est construit."""
    texte = _texte(valeur)
    return texte if texte.startswith("https://") else None


def _apercu(resultat: dict[str, Any], lue_le: datetime) -> dict[str, Any] | None:
    """Vignette et images clés servies par Oriane ; `None` quand elle n'en sert aucune."""
    vignette = _adresse(resultat.get("thumbnailMediaUrl"))
    images: list[str] = []
    for m in _media(resultat):
        frames = m.get("frames")
        for frame in frames if isinstance(frames, list) else []:
            adresse = _adresse(frame.get("url")) if isinstance(frame, dict) else None
            if adresse and adresse not in images:
                images.append(adresse)
    if vignette is None and not images:
        return None
    return {
        "vignette": vignette,
        "images_cles": images[:LIMITE_IMAGES_CLES],
        "source": "Oriane",
        "lue_le": lue_le,
    }


def nom_requete(origine: str, phrase: str) -> str:
    """Nom d'une sous-requête : `dit:`, `ecrit:` ou `mots:` suivi de la variante (rendu par Oriane)."""
    return f"{origine}:{phrase}"


def _noms_trouves(resultat: dict[str, Any]) -> list[str] | None:
    noms = resultat.get("matchedQueries")
    return [n for n in noms if isinstance(n, str)] if isinstance(noms, list) else None


def phrases_trouvees(
    resultat: dict[str, Any], phrases: Sequence[str], noyaux: Sequence[str] = ()
) -> list[str]:
    """Variantes (phrases exactes ou noyaux de mots) dont une sous-requête `dit:`, `ecrit:` ou `mots:` a
    trouvé le résultat, dans l'ordre de la recherche.

    Relevé réel du 09/11 (F020c) : `includesFuzzy` rend des résultats que `matchedQueries` ne nomme pas
    (32 sur 100 pour deux noyaux, 22 sur 31 pour un seul : seuls `dit_ou_ecrit` et le nom racine figurent).
    Une phrase exacte, elle, est toujours nommée. Un résultat rendu par Oriane (liste `matchedQueries`
    présente) qu'aucune variante ne nomme a donc été trouvé par un noyau : on le rattache au premier noyau,
    le plus général, plutôt que de le perdre du récit.
    """
    noms_trouves = _noms_trouves(resultat)
    noms = set(noms_trouves or [])
    trouvees = [
        p
        for p in phrases
        if any(nom_requete(origine, p) in noms for origine in (REQUETE_DIT, REQUETE_ECRIT, REQUETE_MOTS))
    ]
    if not trouvees and noms_trouves is not None and noyaux:
        return [noyaux[0]]
    return trouvees


def compter_origines(resultats: list[dict[str, Any]]) -> dict[str, int]:
    """Résultats trouvés par la parole (`dits`), par l'écran (`ecrits`) ou sans origine connue."""
    dits = ecrits = sans_origine = 0
    for r in resultats:
        noms = _noms_trouves(r)
        if noms is None:
            sans_origine += 1
            continue
        dits += any(n.startswith(REQUETE_DIT + ":") for n in noms)
        ecrits += any(n.startswith(REQUETE_ECRIT + ":") for n in noms)
    return {"dits": dits, "ecrits": ecrits, "sans_origine": sans_origine}


def projeter(
    resultat: dict[str, Any],
    *,
    lue_le: datetime | None = None,
    phrases: Sequence[str] = (),
    noyaux: Sequence[str] = (),
) -> Video:
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
    donnees: dict[str, Any] = {
        "identifiant": identifiant,
        "plateforme": plateforme,
        "identifiant_plateforme": identifiant_plateforme,
        "compte": compte,
        "publie_le": publie_le,
        "vues_selon_oriane": _compte(resultat.get("viewsCount")),
        "interactions_selon_oriane": _compte(resultat.get("interactionsCount")),
        "legende": _texte(resultat.get("caption")),
        "requetes_trouvees": phrases_trouvees(resultat, phrases, noyaux),
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
    apercu = _apercu(resultat, lue_le)
    if apercu is not None:
        donnees["apercu"] = apercu
    try:
        return Video.model_validate(donnees)
    except (
        ValueError
    ) as exc:  # la validation pydantic hérite de ValueError ; son détail peut citer des valeurs
        raise ResultatIllisible("résultat non conforme à video.v1") from exc
