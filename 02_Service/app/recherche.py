"""Recherche à la demande (S13) : une question ou un lien collé devient des filtres affichés avant lancement.

Deux temps, deux fonctions :

- `preparer` traduit la question en filtres (`recherche.v1`) sans appeler Oriane ;
- `executer` rejoue cette traduction auprès d'Oriane (une page), écrit les vidéos, ajoute le récit de la
  phrase au radar, ou rend la vidéo du lien. En mode enregistré, il sert le cas sans appel.

La traduction est déterministe et sans modèle de langue : guillemets, expressions de temps, exclusion de
comptes, plateformes, liens. Une expression de temps ou de plateforme écrite hors guillemets est lue comme
une consigne ; la phrase entre guillemets n'est jamais retouchée. Les filtres affichés sont ceux qui
partent : `executer` les passe tels quels à `oriane.rechercher`.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI

from app import base, cas
from app.acquisition import (
    ECHECS_AVANT_BASCULE,
    METHODE_COUT,
    PANNES,
    basculer,
    credits_du_jour,
    enregistre_le_courant,
    suivi_de,
)
from app.config import Configuration
from app.erreurs import ErreurApi
from app.liste_blanche import LONGUEUR_MAX_PHRASE
from app.modeles import (
    DANS_PAROLE_OU_ECRAN,
    VIDEO_V1,
    CoutEstime,
    Fenetre,
    FiltresRecherche,
    Recherche,
    RefusRecherche,
    ResultatRecherche,
    Video,
)
from app.mots import normaliser
from app.oriane import (
    CREDITS_PAR_PAGE_DEFAULT,
    CreditsEpuises,
    OrianeInjoignable,
    rechercher,
)
from app.recits import calculer_recits, cle_phrase, identifiant_recit

journal = logging.getLogger("tete_de_brut")

JOURS_PAR_DEFAUT = 7
JOURS_MAXIMUM = 365
MESSAGE_HORS_CAS = "Mode enregistré : seules les phrases du cas sont servies"
DETAIL_NOM_SEUL = (
    "Une recherche sur le seul nom d'une personne est refusée : cherche une phrase, une image ou un thème."
)
METHODE_SANS_APPEL = "aucun appel à Oriane : la recherche est refusée"
METHODE_ENREGISTRE = METHODE_COUT + " ; en mode enregistré, aucun appel n'est fait : 0 crédit dépensé"
ROUTE_REJEU = "recherche.rejeu"
PREFIXE_DOCUMENT = "recherche-"

# --- lecture de la question -----------------------------------------------------------------------

_GUILLEMETS = re.compile(r"«\s*(.*?)\s*»|“\s*(.*?)\s*”|\"\s*(.*?)\s*\"", re.S)
_LIEN = re.compile(
    r"(?<![\w@.-])((?:https?://)?(?:[\w-]+\.)*(?:tiktok\.com|instagram\.com|youtube\.com|youtu\.be)"
    r"(?![\w.-])(?:[/?#]\S*)?)",
    re.I,
)
_EXCLUSION = re.compile(
    r"\b(?:hors|sans)\s+(?:les\s+|des\s+)?comptes?\s+(?:de\s+|d['’]\s*)?(?P<categorie>[^\W\d_]+)"
    r"(?:\s+politiques?)?",
    re.I,
)
_DEPUIS_N = re.compile(r"\bdepuis\s+(?P<n>\d+)\s+jours?\b", re.I)
_DEPUIS_HIER = re.compile(r"\bdepuis\s+hier\b", re.I)
_HEURES = re.compile(
    r"\b(?:(?:dans|sur)\s+)?(?:les\s+)?(?:dernières?\s+)?(?P<h>24|48)\s*(?:h|heures?)\b", re.I
)
_SEPT_JOURS = re.compile(r"\b(?:(?:dans|sur)\s+)?(?:les\s+)?7\s+(?:derniers?\s+)?jours\b", re.I)
_NOM_PLATEFORME = r"(?:tiktok|instagram|youtube)"
_PLATEFORMES = re.compile(
    rf"(?:\b(?:sur|dans|via)\s+)?\b{_NOM_PLATEFORME}\b(?:\s*(?:,|\bet\b|\bou\b)\s*\b{_NOM_PLATEFORME}\b)*",
    re.I,
)
_AMORCE = re.compile(
    r"^\s*(?:que\s+dit[- ]on|que\s+disent[- ]ils|qui\s+parle|on\s+parle)"
    r"\s*(?:de\s+|du\s+|des\s+|d['’]\s*|sur\s+)?",
    re.I,
)
_MOT = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")
_HOTES = {
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}
_ID_TIKTOK = re.compile(r"^/@[^/]+/video/(\d+)")
_ID_INSTAGRAM = re.compile(r"^/(?:[^/]+/)?(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)")
_ID_YOUTUBE = re.compile(r"^/(?:shorts|embed|live)/([A-Za-z0-9_-]{6,20})")
_ID_COURT = re.compile(r"^/([A-Za-z0-9_-]{6,20})$")
_DETAIL_LIEN = (
    "Ce lien ne donne pas l'identifiant d'une vidéo : colle le lien complet d'une vidéo TikTok, "
    "Instagram ou YouTube (pas un lien raccourci ni un lien de compte)."
)


def _sans_accent(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in decompose if not unicodedata.combining(c))


@dataclass(frozen=True)
class Traduction:
    """Ce que la question veut dire : type, filtres, refus éventuel et ce qui n'a pas pu s'appliquer."""

    type: str
    filtres: FiltresRecherche
    refus: RefusRecherche | None = None
    notes: list[str] = field(default_factory=list)
    plateforme_lien: str | None = None
    exclusion: str | None = None  # libellé de la liste de comptes écartée, s'il y en a une


def lire_listes_de_comptes(config: Configuration) -> tuple[dict[str, list[str]], str | None]:
    """Listes de comptes à écarter (`{"partis": [...]}`) et, si elle est inutilisable, la raison en clair."""
    if config.chemin_comptes is None:
        return {}, None
    try:
        document = json.loads(Path(config.chemin_comptes).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, "la liste de comptes configurée est introuvable"
    except (OSError, ValueError):
        return {}, "la liste de comptes configurée est illisible"
    if not isinstance(document, dict) or not all(
        isinstance(v, list) and all(isinstance(c, str) for c in v) for v in document.values()
    ):
        return {}, "la liste de comptes configurée est mal formée"
    listes = {
        str(nom): list(dict.fromkeys(c.strip().lstrip("@") for c in comptes if c.strip().lstrip("@")))
        for nom, comptes in document.items()
    }
    return listes, None


def _chercher_liste(categorie: str, listes: dict[str, list[str]]) -> tuple[str, list[str]] | None:
    """Liste de comptes dont le nom est la catégorie dite, au pluriel ou au singulier, sans accent."""
    voulu = _sans_accent(categorie)
    for nom, comptes in listes.items():
        nom_normalise = _sans_accent(nom)
        if voulu in (nom_normalise, nom_normalise + "s") or voulu + "s" == nom_normalise:
            return nom, comptes
    return None


def est_nom_seul(phrase: str) -> bool:
    """RG-02 : une phrase de un à trois mots, tous en capitale initiale et sans chiffre, est un nom."""
    mots = _MOT.findall(phrase)
    return 1 <= len(mots) <= 3 and all(m[0].isupper() for m in mots) and not any(c.isdigit() for c in phrase)


def _lire_lien(question: str) -> tuple[str, str] | None | bool:
    """Lien de vidéo de la question : (plateforme, identifiant), `False` s'il est illisible, `None` sinon."""
    trouve = _LIEN.search(question)
    if trouve is None:
        return None
    adresse = trouve.group(1).rstrip(".,;:!?)»”\"'")
    analyse = urlparse(adresse if "://" in adresse else "https://" + adresse)
    hote = (analyse.hostname or "").lower()
    domaine = next((d for d in _HOTES if hote == d or hote.endswith("." + d)), None)
    if domaine is None:
        return None
    plateforme, chemin = _HOTES[domaine], analyse.path
    if plateforme == "tiktok":
        correspondance = _ID_TIKTOK.match(chemin)
    elif plateforme == "instagram":
        correspondance = _ID_INSTAGRAM.match(chemin)
    elif domaine == "youtu.be":
        correspondance = _ID_COURT.match(chemin)
    else:
        identifiants = parse_qs(analyse.query).get("v", [])
        if chemin == "/watch" and identifiants and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", identifiants[0]):
            return plateforme, identifiants[0]
        correspondance = _ID_YOUTUBE.match(chemin)
    return (plateforme, correspondance.group(1)) if correspondance else False


def _jours(texte: str) -> tuple[str, int | None]:
    """Retire les expressions de temps et rend le nombre de jours de la première."""
    trouves: list[tuple[int, int]] = []
    for motif, valeur in (
        (_DEPUIS_N, lambda m: int(m.group("n"))),
        (_DEPUIS_HIER, lambda m: 1),
        (_HEURES, lambda m: 1 if m.group("h") == "24" else 2),
        (_SEPT_JOURS, lambda m: 7),
    ):
        trouves += [(m.start(), valeur(m)) for m in motif.finditer(texte)]
        texte = motif.sub(" ", texte)
    return texte, (min(trouves)[1] if trouves else None)


def _phrase_libre(reste: str) -> str:
    """Question débarrassée de son amorce et de la ponctuation qui l'entoure."""
    sans_amorce = _AMORCE.sub("", reste, count=1)
    return re.sub(r"\s+", " ", sans_amorce).strip(" \t\n?!.,;:-–—")


def _fenetre(jours: int | None, maintenant: datetime) -> Fenetre:
    jours = min(max(jours or JOURS_PAR_DEFAUT, 1), JOURS_MAXIMUM)
    debut = datetime.combine((maintenant - timedelta(days=jours)).date(), time.min, tzinfo=UTC)
    return Fenetre(debut=debut, fin=maintenant.replace(microsecond=0))


def traduire(question: str, config: Configuration, maintenant: datetime) -> Traduction:
    """Traduit la question en filtres ; ne lit que la question et le fichier des listes de comptes."""
    lien = _lire_lien(question)
    if lien is False:
        refus = RefusRecherche(code="lien_non_reconnu", detail=_DETAIL_LIEN)
        return Traduction("lien", FiltresRecherche(), refus)
    if lien:
        plateforme, identifiant = lien
        filtres = FiltresRecherche(plateformes=[plateforme], identifiant_plateforme=identifiant)  # type: ignore[list-item]
        return Traduction("lien", filtres, plateforme_lien=plateforme)

    entre_guillemets: list[str] = []

    def garder(trouve: re.Match[str]) -> str:
        entre_guillemets.append(next(g for g in trouve.groups() if g is not None))
        return " "

    reste = _GUILLEMETS.sub(garder, question)
    reste, categorie = _exclusion(reste)
    reste, jours = _jours(reste)
    plateformes: list[str] = []

    def lire_plateformes(trouve: re.Match[str]) -> str:
        plateformes.extend(re.findall(_NOM_PLATEFORME, trouve.group(0), re.I))
        return " "

    reste = _PLATEFORMES.sub(lire_plateformes, reste)
    plateformes = list(dict.fromkeys(p.lower() for p in plateformes))

    if entre_guillemets:
        phrases = [p for p in entre_guillemets if p.strip()]
        if not phrases:
            return _refuser(
                "aucune_phrase", "La phrase entre guillemets est vide : écris la phrase cherchée."
            )
        if len(phrases) > 1:
            return _refuser(
                "plusieurs_phrases",
                "Une recherche porte sur une seule phrase : garde une phrase entre guillemets.",
            )
        phrase = phrases[0].strip()
    else:
        phrase = _phrase_libre(reste)
    if not normaliser(phrase):
        return _refuser(
            "aucune_phrase", "Aucune phrase à chercher : écris la phrase, de préférence entre guillemets."
        )
    if len(phrase) > LONGUEUR_MAX_PHRASE:
        return _refuser(
            "phrase_trop_longue", f"La phrase dépasse {LONGUEUR_MAX_PHRASE} caractères : raccourcis-la."
        )

    notes: list[str] = []
    comptes_exclus: list[str] = []
    exclusion: str | None = None
    if categorie is not None:
        listes, probleme = lire_listes_de_comptes(config)
        liste = _chercher_liste(categorie, listes)
        if liste is not None and liste[1]:
            exclusion, comptes_exclus = liste[0], liste[1]
        else:
            pourquoi = probleme or f"aucune liste de comptes « {categorie} » n'est configurée"
            notes.append(f"exclusion « comptes de {categorie} » non appliquée : {pourquoi}")

    filtres = FiltresRecherche(
        phrases=[phrase],
        dans=DANS_PAROLE_OU_ECRAN,
        fenetre=_fenetre(jours, maintenant),
        comptes_exclus=comptes_exclus,
        plateformes=plateformes,  # type: ignore[arg-type]
    )
    refus = RefusRecherche(code="nom_seul", detail=DETAIL_NOM_SEUL) if est_nom_seul(phrase) else None
    return Traduction("phrase", filtres, refus, notes, exclusion=exclusion)


def _exclusion(texte: str) -> tuple[str, str | None]:
    """Retire « hors comptes de <catégorie> » et rend la catégorie dite."""
    trouve = _EXCLUSION.search(texte)
    if trouve is None:
        return texte, None
    return _EXCLUSION.sub(" ", texte), trouve.group("categorie")


def _refuser(code: str, detail: str) -> Traduction:
    return Traduction("phrase", FiltresRecherche(), RefusRecherche(code=code, detail=detail))  # type: ignore[arg-type]


# --- préparation ----------------------------------------------------------------------------------


def _requete_en_clair(traduction: Traduction) -> str:
    filtres = traduction.filtres
    if traduction.refus is not None:
        return "recherche refusée : rien n'est envoyé à Oriane"
    if traduction.type == "lien":
        if filtres.identifiant_plateforme is None:
            return "recherche refusée : rien n'est envoyé à Oriane"
        return (
            f"vidéo {traduction.plateforme_lien} d'identifiant {filtres.identifiant_plateforme}, "
            "niveau default, sans phrase ni fenêtre"
        )
    if not filtres.phrases or filtres.fenetre is None:
        return "recherche refusée : rien n'est envoyé à Oriane"
    morceaux = [
        f"phrase exacte « {filtres.phrases[0]} », dite ou écrite à l'écran, niveau default, "
        f"du {filtres.fenetre.debut.date().isoformat()} au {filtres.fenetre.fin.date().isoformat()}"
    ]
    if filtres.plateformes:
        morceaux.append("sur " + ", ".join(filtres.plateformes))
    if filtres.comptes_exclus:
        morceaux.append(f"hors {len(filtres.comptes_exclus)} comptes de la liste « {traduction.exclusion} »")
    return ", ".join(morceaux) + "".join(f" ; {note}" for note in traduction.notes)


def preparer(question: str, config: Configuration, *, maintenant: datetime | None = None) -> Recherche:
    """Traduit la question en `recherche.v1` : filtres, requête en clair, coût estimé ; aucun appel Oriane."""
    traduction = traduire(question, config, (maintenant or datetime.now(UTC)).astimezone(UTC))
    if traduction.refus is not None:
        cout = CoutEstime(credits_estimes=0, methode=METHODE_SANS_APPEL)
    else:
        pages = max(len(traduction.filtres.phrases), 1)
        methode = METHODE_ENREGISTRE if config.mode == "enregistre" else METHODE_COUT
        cout = CoutEstime(credits_estimes=pages * CREDITS_PAR_PAGE_DEFAULT, methode=methode)
    enregistre = config.mode == "enregistre"
    return Recherche(
        mode=config.mode,  # type: ignore[arg-type]
        enregistre_le=enregistre_le_courant(config) if enregistre else None,
        question=question,
        type=traduction.type,  # type: ignore[arg-type]
        filtres=traduction.filtres,
        requete_en_clair=_requete_en_clair(traduction),
        cout_estime=cout,
        refus=traduction.refus,
    )


# --- exécution ------------------------------------------------------------------------------------


def _couples(recherche: Recherche) -> list[tuple[str, str]]:
    filtres = recherche.filtres
    if recherche.type != "lien" or filtres.identifiant_plateforme is None:
        return []
    return [(filtres.plateformes[0], filtres.identifiant_plateforme)]


def _recit_de(phrase: str, mode: str) -> Any:
    """Récit de la phrase tel que le radar le sert maintenant."""
    recits, _ = calculer_recits(mode)
    cible = identifiant_recit(phrase)
    return next((r for r in recits if r.identifiant == cible), None)


def _rejouer(config: Configuration, recherche: Recherche) -> ResultatRecherche:
    """Mode enregistré : sert le cas sans appel, ou dit que la recherche n'y est pas."""
    try:
        rejoue = cas.charger(config, avec_videos=True)
    except cas.CasInvalide:
        rejoue = None
    filtres = recherche.filtres
    if recherche.type == "lien":
        video = None
        if rejoue is not None:
            video = next(
                (
                    v
                    for v in rejoue.videos
                    if v.plateforme == filtres.plateformes[0]
                    and v.identifiant_plateforme == filtres.identifiant_plateforme
                ),
                None,
            )
        if video is None:
            raise ErreurApi("introuvable", "Cette vidéo n'est pas dans le cas enregistré.", 404)
        recit = None
    else:
        recit = None
        if rejoue is not None and cle_phrase(filtres.phrases[0]) in {cle_phrase(p) for p in rejoue.phrases}:
            recit = _recit_de(filtres.phrases[0], "enregistre")
        if recit is None:
            raise ErreurApi("recherche_indisponible", MESSAGE_HORS_CAS, 409)
        video = None
    base.consigner(
        route=ROUTE_REJEU,
        cible="recherche rejouée depuis le cas enregistré, sans appel à Oriane",
        mode="enregistre",
    )
    return ResultatRecherche(
        mode="enregistre",
        enregistre_le=recherche.enregistre_le,
        recherche=recherche,
        recit=recit,
        video=video,
    )


def _fusionner(avant: dict[str, list[str]], videos: list[Video]) -> list[Video]:
    """Ajoute aux phrases trouvées d'une vidéo celles d'une recherche précédente, puis réécrit la vidéo.

    `rechercher` écrit la vidéo avec les seules phrases de son appel : sans cette fusion, une seconde
    recherche ferait sortir la vidéo du récit de la première.
    """
    fusionnees: list[Video] = []
    for video in videos:
        anciennes = avant.get(video.identifiant, [])
        connues = {cle_phrase(p) for p in video.requetes_trouvees}
        ajoutees = [p for p in anciennes if cle_phrase(p) not in connues]
        if ajoutees:
            video = video.model_copy(update={"requetes_trouvees": [*video.requetes_trouvees, *ajoutees]})
            base.ecrire("video", video.identifiant, VIDEO_V1, video.model_dump(mode="json"))
        fusionnees.append(video)
    return fusionnees


def _surveiller(recherche: Recherche) -> None:
    """Ajoute la phrase aux phrases surveillées : le radar sert ensuite son récit."""
    phrase, fenetre = recherche.filtres.phrases[0], recherche.filtres.fenetre
    assert fenetre is not None
    base.ecrire(
        cas.TYPE_CAS,
        PREFIXE_DOCUMENT + identifiant_recit(phrase),
        cas.CAS_V1,
        {
            "phrases": [phrase],
            "requete": recherche.requete_en_clair,
            "fenetre": fenetre.model_dump(mode="json"),
        },
    )


async def executer(app: FastAPI, question: str) -> ResultatRecherche:
    """Prépare la question puis la lance : appel Oriane en direct, cas rejoué en mode enregistré.

    Refus (RG-02 et autres) : 422 `validation` avec le libellé du refus, sans aucun appel. Mêmes
    bascules en mode enregistré que l'actualisation du radar : plafond de crédits du jour atteint,
    crédits épuisés (402), deux pannes d'Oriane de suite.
    """
    config: Configuration = app.state.config
    recherche = preparer(question, config)
    if recherche.refus is not None:
        raise ErreurApi("validation", recherche.refus.detail, 422)
    if config.mode == "enregistre":
        return _rejouer(config, recherche)

    depenses = credits_du_jour()
    if depenses + recherche.cout_estime.credits_estimes > config.plafond_credits_jour:
        raison = (
            f"plafond de crédits du jour atteint ({depenses} sur {config.plafond_credits_jour}) : "
            "le service rejoue le cas enregistré"
        )
        basculer(app, raison)
        return _rejouer(app.state.config, preparer(question, app.state.config))

    filtres = recherche.filtres
    avant = {d["identifiant"]: d.get("requetes_trouvees", []) for d in base.lister("video")}
    suivi = suivi_de(app)
    try:
        resultat = await rechercher(
            filtres.phrases,
            filtres.comptes,
            filtres.fenetre,
            config=config,
            plateformes=filtres.plateformes,
            comptes_exclus=filtres.comptes_exclus,
            identifiants_plateforme=_couples(recherche),
            transport=getattr(app.state, "transport_oriane", None),
        )
    except CreditsEpuises:
        basculer(app, "crédits Oriane épuisés (402) : le service rejoue le cas enregistré")
        return _rejouer(app.state.config, preparer(question, app.state.config))
    except OrianeInjoignable as exc:
        if not exc.raison.startswith(PANNES):
            raise  # clé refusée, requête refusée : une panne de configuration, pas de bascule
        suivi.pannes_de_suite += 1
        if suivi.pannes_de_suite < ECHECS_AVANT_BASCULE:
            raise
        basculer(
            app,
            f"Oriane injoignable : {suivi.pannes_de_suite} échecs de suite (dernier : {exc.raison}) ; "
            "le service rejoue le cas enregistré",
        )
        suivi.pannes_de_suite = 0
        return _rejouer(app.state.config, preparer(question, app.state.config))
    suivi.pannes_de_suite = 0

    videos = _fusionner(avant, resultat.videos)
    if recherche.type == "lien":
        video = next(
            (
                v
                for v in videos
                if v.plateforme == filtres.plateformes[0]
                and v.identifiant_plateforme == filtres.identifiant_plateforme
            ),
            None,
        )
        if video is None:
            raise ErreurApi("introuvable", "Oriane n'a retrouvé aucune vidéo avec ce lien.", 404)
        return ResultatRecherche(mode="direct", recherche=recherche, video=video)
    _surveiller(recherche)
    recit = _recit_de(filtres.phrases[0], "direct")
    return ResultatRecherche(mode="direct", recherche=recherche, recit=recit)
