"""Recherche à la demande (S13) : une question ou un lien collé devient des filtres affichés avant lancement.

Deux temps, deux fonctions :

- `preparer` traduit la question en filtres (`recherche.v1`) sans appeler Oriane ;
- `executer` rejoue cette traduction auprès d'Oriane (une page), écrit les vidéos, ajoute au radar le récit
  unique de la recherche, ou rend la vidéo du lien. En mode enregistré, il sert le cas sans appel.

Deux traductions, jamais mêlées. Déterministe : guillemets, expressions de temps, exclusion de comptes,
plateformes, liens ; une expression de temps ou de plateforme écrite hors guillemets est lue comme une
consigne, la phrase entre guillemets n'est jamais retouchée (phrase exacte, jamais un noyau). Par le modèle
de langue (F018, F020) : une question libre, sans guillemets ni lien, est reformulée en noyaux de mots
(cherchés dans n'importe quel ordre : la couverture) et en phrases exactes (la précision), avec une
fenêtre, des exclusions et des plateformes (`app/recherche_modele.py`) ; toute erreur du modèle ramène à la
traduction déterministe, dont le noyau est formé des mots pleins de la question. Les filtres affichés sont
ceux qui partent : `executer` les passe tels quels à `oriane.rechercher`. Une recherche = un récit, quel que
soit le nombre de variantes.
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
from starlette.concurrency import run_in_threadpool

from app import base, cas
from app.acquisition import (
    ECHECS_AVANT_BASCULE,
    METHODE_COUT,
    PANNES,
    basculer,
    credits_du_jour,
    enregistre_le_courant,
    suivi_de,
    verrou_credits,
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
from app.recherche_modele import Reformulation, reformuler
from app.recits import (
    NON_CHERCHE,
    calculer_recits,
    cle_phrase,
    construire_recit,
    identifiant_recit,
    lire_videos,
    phrases_surveillees,
    recherche_de,
    reunir_variantes,
    verifier_cas,
)

journal = logging.getLogger("tete_de_brut")

JOURS_PAR_DEFAUT = 30
JOURS_MAXIMUM = 365
MESSAGE_HORS_CAS = "Mode enregistré : seules les phrases du cas sont servies"
DETAIL_NOM_SEUL = (
    "Une recherche sur le seul nom d'une personne est refusée : cherche une phrase, une image ou un thème."
)
METHODE_SANS_APPEL = "aucun appel à Oriane : la recherche est refusée"
METHODE_ENREGISTRE = METHODE_COUT + " ; en mode enregistré, aucun appel n'est fait : 0 crédit dépensé"
ROUTE_REJEU = "recherche.rejeu"
PREFIXE_DOCUMENT = cas.PREFIXE_RECHERCHE
PREFIXE_REFORMULATION = "reformulée par un modèle de langue : "
REFORMULATION_MODELE = "modele"
REFORMULATION_DETERMINISTE = "deterministe"

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
MOTS_NOYAU_MAX = 3  # repli déterministe : trois mots pleins au plus, dans l'ordre de la question
# Mots vides du repli déterministe (sans accent, minuscules) : articles, prépositions, pronoms, auxiliaires,
# conjonctions, mots de la demande elle-même (« donne-moi », « infos », « récentes »).
MOTS_VIDES = frozenset(
    """
    le la les l un une des du de d au aux en et ou a sur sous dans par pour avec ce cet cette ces se
    sa son ses mon ma mes ton ta tes notre nos votre vos leur leurs qui que quoi dont est sont etre ete
    avoir ont ai as ne pas plus tres moi toi lui elle il ils elles on nous vous je tu y ca cela ceci
    donne donnez dis dites parle parlez montre montrez trouve trouvez cherche cherchez info infos
    information informations recent recente recents recentes dernier derniere derniers dernieres
    actualite actualites tout tous toute toutes vers chez entre apres avant depuis pendant comme mais
    donc car si ni quand comment pourquoi
    """.split()
)
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
    reformulation: str | None = None  # `modele` ou `deterministe` pour une phrase libre, `None` pour un lien


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


def _variantes_du_modele(reformulation: Reformulation) -> tuple[list[str], list[str]]:
    """Noyaux et phrases du modèle, RG-02 appliquée à chacun : un nom seul est écarté, jamais cherché."""
    noyaux = [n for n in reformulation.noyaux if not est_nom_seul(n)]
    phrases = [p for p in reformulation.phrases if not est_nom_seul(p)]
    return noyaux, phrases


def noyau_de(phrase: str) -> str:
    """Repli déterministe : les mots pleins de la phrase (trois au plus, dans l'ordre), sinon vide."""
    gardes: list[str] = []
    for mot in _MOT.findall(phrase):
        # Mots entiers seulement : « d'achat » et « l'essence » restent tels qu'on les dit (Oriane les lit
        # comme un seul mot), « de » ou « du » séparés par une espace sont retirés.
        if _sans_accent(mot) not in MOTS_VIDES:
            gardes.append(mot)
    return " ".join(gardes[:MOTS_NOYAU_MAX])


def traduire(
    question: str,
    config: Configuration,
    maintenant: datetime,
    reformulation: Reformulation | None = None,
) -> Traduction:
    """Traduit la question en filtres ; ne lit que la question, la reformulation et la liste de comptes.

    `reformulation` n'est prise en compte que pour une question sans lien ni guillemets, et seulement si
    elle porte au moins un noyau ou une phrase qui n'est pas un nom seul ; sinon la traduction est
    déterministe. Un modèle qui dit `personne_seule` fait refuser la question (RG-02), sans appel à Oriane.
    """
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

    avec_modele = reformulation is not None and not entre_guillemets
    if avec_modele and reformulation.personne_seule:  # type: ignore[union-attr]
        refus_nom = RefusRecherche(code="nom_seul", detail=DETAIL_NOM_SEUL)
        return Traduction("phrase", FiltresRecherche(), refus_nom, reformulation=REFORMULATION_MODELE)
    noyaux_modele, phrases_modele = _variantes_du_modele(reformulation) if avec_modele else ([], [])  # type: ignore[arg-type]
    noyaux: list[str]
    phrases: list[str]
    if reformulation is not None and (noyaux_modele or phrases_modele):
        # Ce que la question dit en toutes lettres (« depuis hier », « sur TikTok », « hors comptes de
        # partis ») prime ; le modèle complète ce qu'elle exprime autrement (« cette semaine »).
        noyaux, phrases, mode_reformulation = noyaux_modele, phrases_modele, REFORMULATION_MODELE
        jours = jours if jours is not None else reformulation.jours
        plateformes = plateformes or list(reformulation.plateformes)
        categories = [categorie] if categorie is not None else list(reformulation.exclusions)
    else:
        mode_reformulation = REFORMULATION_DETERMINISTE
        categories = [categorie] if categorie is not None else []
        if entre_guillemets:
            gardees = [p for p in entre_guillemets if p.strip()]
            if not gardees:
                return _refuser(
                    "aucune_phrase", "La phrase entre guillemets est vide : écris la phrase cherchée."
                )
            if len(gardees) > 1:
                return _refuser(
                    "plusieurs_phrases",
                    "Une recherche porte sur une seule phrase : garde une phrase entre guillemets.",
                )
            phrase = gardees[0].strip()
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
        # Une phrase entre guillemets reste une phrase exacte ; une question libre devient un noyau de
        # mots pleins, ou, faute de mot plein, la question nettoyée en phrase exacte.
        noyau = "" if entre_guillemets else noyau_de(phrase)
        noyaux, phrases = ([noyau], []) if noyau else ([], [phrase])

    notes: list[str] = []
    comptes_exclus: list[str] = []
    exclusions: list[str] = []
    if categories:
        listes, probleme = lire_listes_de_comptes(config)
        for demandee in dict.fromkeys(categories):
            liste = _chercher_liste(demandee, listes)
            if liste is not None and liste[1]:
                exclusions.append(liste[0])
                comptes_exclus.extend(c for c in liste[1] if c not in comptes_exclus)
            else:
                pourquoi = probleme or f"aucune liste de comptes « {demandee} » n'est configurée"
                notes.append(f"exclusion « comptes de {demandee} » non appliquée : {pourquoi}")

    filtres = FiltresRecherche(
        phrases=[*noyaux, *phrases],
        noyaux=noyaux,
        dans=DANS_PAROLE_OU_ECRAN,
        fenetre=_fenetre(jours, maintenant),
        comptes_exclus=comptes_exclus,
        plateformes=plateformes,  # type: ignore[arg-type]
    )
    refus = (
        RefusRecherche(code="nom_seul", detail=DETAIL_NOM_SEUL)
        if any(est_nom_seul(p) for p in filtres.phrases)
        else None
    )
    return Traduction(
        "phrase",
        filtres,
        refus,
        notes,
        exclusion=", ".join(exclusions) or None,
        reformulation=mode_reformulation,
    )


def _exclusion(texte: str) -> tuple[str, str | None]:
    """Retire « hors comptes de <catégorie> » et rend la catégorie dite."""
    trouve = _EXCLUSION.search(texte)
    if trouve is None:
        return texte, None
    return _EXCLUSION.sub(" ", texte), trouve.group("categorie")


def _refuser(code: str, detail: str) -> Traduction:
    return Traduction(
        "phrase",
        FiltresRecherche(),
        RefusRecherche(code=code, detail=detail),  # type: ignore[arg-type]
        reformulation=REFORMULATION_DETERMINISTE,
    )


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
    exactes = [p for p in filtres.phrases if p not in filtres.noyaux]
    citer = lambda variantes: ", ".join(f"« {v} »" for v in variantes)  # noqa: E731
    if filtres.noyaux:
        aussi_tels_quels = any(len(n.split()) >= 2 for n in filtres.noyaux)
        cherche = [
            f"mots {citer(filtres.noyaux)} en tout ordre"
            + (" (et aussi tels quels, en phrase exacte)" if aussi_tels_quels else "")
        ]
        if exactes:
            nombre = "phrases exactes" if len(exactes) > 1 else "phrase exacte"
            cherche.append(f"{nombre} {citer(exactes)}")
        phrases = " ; ".join(cherche) + ", dits ou écrits à l'écran"
    elif len(exactes) == 1:
        phrases = f"phrase exacte « {exactes[0]} », dite ou écrite à l'écran"
    else:
        phrases = f"phrases exactes {citer(exactes)}, dites ou écrites à l'écran"
    morceaux = [
        f"{phrases}, niveau default, "
        f"du {filtres.fenetre.debut.date().isoformat()} au {filtres.fenetre.fin.date().isoformat()}"
    ]
    if filtres.plateformes:
        morceaux.append("sur " + ", ".join(filtres.plateformes))
    if filtres.comptes_exclus:
        morceaux.append(f"hors {len(filtres.comptes_exclus)} comptes de la liste « {traduction.exclusion} »")
    en_clair = ", ".join(morceaux) + "".join(f" ; {note}" for note in traduction.notes)
    if traduction.reformulation == REFORMULATION_MODELE:
        return PREFIXE_REFORMULATION + en_clair
    return en_clair


def _a_reformuler(question: str, config: Configuration) -> bool:
    """Vrai si la question libre part chez le modèle : mode actif, ni lien ni phrase entre guillemets."""
    return (
        config.reformulation_par_modele
        and _lire_lien(question) is None
        and _GUILLEMETS.search(question) is None
    )


def preparer(question: str, config: Configuration, *, maintenant: datetime | None = None) -> Recherche:
    """Traduit la question en `recherche.v1` : filtres, requête en clair, coût ; aucun appel Oriane.

    Une question libre est reformulée par le modèle de langue quand sa clé est présente (appel bloquant,
    8 s au plus, repli déterministe sur toute erreur) ; l'appelant asynchrone passe par un fil.
    """
    reformulation = reformuler(question, config) if _a_reformuler(question, config) else None
    traduction = traduire(question, config, (maintenant or datetime.now(UTC)).astimezone(UTC), reformulation)
    if traduction.refus is not None:
        cout = CoutEstime(credits_estimes=0, methode=METHODE_SANS_APPEL)
    else:
        # Une seule requête, une page : toutes les phrases partent ensemble en sous-requête `or`.
        methode = METHODE_ENREGISTRE if config.mode == "enregistre" else METHODE_COUT
        cout = CoutEstime(credits_estimes=CREDITS_PAR_PAGE_DEFAULT, methode=methode)
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
        reformulation=traduction.reformulation,  # type: ignore[arg-type]
    )


# --- exécution ------------------------------------------------------------------------------------


def _couples(recherche: Recherche) -> list[tuple[str, str]]:
    filtres = recherche.filtres
    if recherche.type != "lien" or filtres.identifiant_plateforme is None:
        return []
    return [(filtres.plateformes[0], filtres.identifiant_plateforme)]


def _pivot(filtres: FiltresRecherche) -> str:
    """Pivot de la recherche : le premier noyau, sinon la première phrase (c'est la phrase du récit)."""
    return filtres.noyaux[0] if filtres.noyaux else filtres.phrases[0]


def _recit_rejoue(variantes: list[str]) -> Any | None:
    """Récit du cas rejoué pour des variantes connues du cas : l'union de leurs vidéos, comptées une fois."""
    recits, calcule_le = calculer_recits("enregistre")
    premier = next((r for r in recits if r.identifiant == identifiant_recit(variantes[0])), None)
    if premier is None or len(variantes) == 1:
        return premier
    videos = lire_videos(base.lister("video"))
    cas_valides = [d for d in base.lister(cas.TYPE_CAS) if verifier_cas(d) is None]
    entree = phrases_surveillees(cas_valides, videos).get(cle_phrase(variantes[0]))
    if entree is None:
        return premier
    ignores = [s.texte for s in premier.non_cherche[len(NON_CHERCHE) :] if s.texte]
    return construire_recit(
        {**entree, "variantes": variantes}, videos, calcule_le, "enregistre", premier.enregistre_le, ignores
    )


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
        if rejoue is not None:
            connues = {cle_phrase(p) for p in rejoue.phrases}
            dans_le_cas = [p for p in filtres.phrases if cle_phrase(p) in connues]
            recit = _recit_rejoue(dans_le_cas) if dans_le_cas else None
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


def _surveiller(recherche: Recherche) -> str:
    """Écrit le document de la recherche (pivot et variantes) : une recherche = un récit au radar, même vide.

    Une recherche qui reprend un pivot déjà surveillé garde les variantes de la précédente. Rend le pivot.
    """
    fenetre = recherche.filtres.fenetre
    assert fenetre is not None
    pivot = _pivot(recherche.filtres)
    identifiant = PREFIXE_DOCUMENT + identifiant_recit(pivot)
    variantes = list(recherche.filtres.phrases)
    noyaux = list(recherche.filtres.noyaux)
    ancien = base.lire(cas.TYPE_CAS, identifiant)
    anciennes = recherche_de(ancien) if isinstance(ancien, dict) else None
    if anciennes is not None:
        variantes = reunir_variantes(variantes, anciennes[1])
        noyaux = reunir_variantes(noyaux, ancien.get("noyaux") or [])
    base.ecrire(
        cas.TYPE_CAS,
        identifiant,
        cas.CAS_V1,
        {
            "pivot": pivot,
            "variantes": variantes,
            "noyaux": noyaux,
            "requete": recherche.requete_en_clair,
            "fenetre": fenetre.model_dump(mode="json"),
        },
    )
    return pivot


async def _preparer_en_fil(question: str, config: Configuration) -> Recherche:
    """`preparer` dans un fil : l'appel au modèle de langue bloque jusqu'à 8 s, pas la boucle d'événements."""
    return await run_in_threadpool(preparer, question, config)


async def executer(app: FastAPI, question: str) -> ResultatRecherche:
    """Prépare la question puis la lance : appel Oriane en direct, cas rejoué en mode enregistré.

    Une question libre cherche tous les noyaux et toutes les phrases rendus en une page (sous-requête `or`)
    et rend un récit unique, celui de la recherche (pivot et variantes), même s'il est vide.

    Refus (RG-02 et autres) : 422 `validation` avec le libellé du refus, sans aucun appel. Mêmes
    bascules en mode enregistré que l'actualisation du radar : plafond de crédits du jour atteint,
    crédits épuisés (402), deux pannes d'Oriane de suite.
    """
    config: Configuration = app.state.config
    recherche = await _preparer_en_fil(question, config)
    if recherche.refus is not None:
        raise ErreurApi("validation", recherche.refus.detail, 422)
    if config.mode == "enregistre":
        return _rejouer(config, recherche)

    # Le verrou décide de la bascule ; le rejeu, qui peut rappeler le modèle de langue, se fait après.
    suivi = suivi_de(app)
    async with verrou_credits(app):
        resultat = None
        if app.state.config.mode != "enregistre":  # sinon une autre demande a basculé pendant l'attente
            config = app.state.config
            depenses = credits_du_jour()
            if depenses + recherche.cout_estime.credits_estimes > config.plafond_credits_jour:
                raison = (
                    f"plafond de crédits du jour atteint ({depenses} sur {config.plafond_credits_jour}) : "
                    "le service rejoue le cas enregistré"
                )
                basculer(app, raison)
            else:
                filtres = recherche.filtres
                avant = {d["identifiant"]: d.get("requetes_trouvees", []) for d in base.lister("video")}
                try:
                    resultat = await rechercher(
                        [p for p in filtres.phrases if p not in filtres.noyaux],
                        filtres.comptes,
                        filtres.fenetre,
                        config=config,
                        plateformes=filtres.plateformes,
                        comptes_exclus=filtres.comptes_exclus,
                        identifiants_plateforme=_couples(recherche),
                        noyaux=filtres.noyaux,
                        transport=getattr(app.state, "transport_oriane", None),
                    )
                except CreditsEpuises:
                    basculer(app, "crédits Oriane épuisés (402) : le service rejoue le cas enregistré")
                except OrianeInjoignable as exc:
                    if not exc.raison.startswith(PANNES):
                        raise  # clé refusée, requête refusée : une panne de configuration, pas de bascule
                    suivi.pannes_de_suite += 1
                    if suivi.pannes_de_suite < ECHECS_AVANT_BASCULE:
                        raise
                    basculer(
                        app,
                        f"Oriane injoignable : {suivi.pannes_de_suite} échecs de suite "
                        f"(dernier : {exc.raison}) ; le service rejoue le cas enregistré",
                    )
                    suivi.pannes_de_suite = 0
    if resultat is None:
        return _rejouer(app.state.config, await _preparer_en_fil(question, app.state.config))
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
    pivot = _surveiller(recherche)
    recits, _ = calculer_recits("direct")
    recit = next((r for r in recits if r.identifiant == identifiant_recit(pivot)), None)
    return ResultatRecherche(mode="direct", recherche=recherche, recit=recit)
