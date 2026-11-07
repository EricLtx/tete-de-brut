"""Contrats du service (`api.v1`) : modèles pydantic partagés par le service et les écrans.

Champs en français et en `snake_case` ; aucun nom de champ Oriane (la correspondance vit dans
`app/liste_blanche.py`). Chaque modèle refuse tout champ supplémentaire (`extra="forbid"`) : c'est
ainsi qu'aucun champ de tiers ne passe. Toute réponse JSON porte `mode` et, en mode enregistré,
`enregistre_le`. Aucun modèle ne porte de champ de qualification (score, verdict).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.libelles import contient_libelle_refuse
from app.mots import NORMALISATION_MOTS_V1

# --- versions des contrats ---------------------------------------------------------------------

API_V1 = "api.v1"
VIDEO_V1 = "video.v1"
RECIT_V1 = "recit.v1"
ECART_V1 = "ecart.v1"
FICHE_V1 = "fiche.v1"
DECISION_V1 = "decision.v1"

# --- vocabulaire fixe --------------------------------------------------------------------------

SOURCE_ORIANE = "Oriane"
NIVEAU_DEFAULT = "default"
LIBELLE_PLUS_ANCIENNE_VERSION = "plus ancienne version retrouvée dans les sources consultées"
LIBELLE_HEURE_NON_FOURNIE = "non fournie au niveau default"
LIMITE_IMAGES_CLES = 10
LIMITE_TRANSCRIPTIONS = "transcriptions lues chez Oriane, non refaites sur la vidéo"
METHODE_GABARIT_V1 = "gabarit v1"

Mode = Literal["direct", "enregistre"]
Plateforme = Literal["instagram", "tiktok", "youtube"]
TypeOperation = Literal["retire", "ajoute", "remplace"]
EtatVersion = Literal["a_trancher", "confirmee", "ecartee"]
ValeurDecision = Literal["a_verifier", "ne_pas_amplifier", "pret_a_traiter"]
TexteNonVide = Annotated[str, Field(min_length=1)]
AdresseHttps = Annotated[str, Field(pattern=r"^https://\S+$")]  # aperçu : https seulement
Position = Annotated[int, Field(ge=0)]
Compte = Annotated[int, Field(ge=0)]


class Modele(BaseModel):
    """Base de tous les contrats : tout champ inconnu est refusé."""

    model_config = ConfigDict(extra="forbid")


class Reponse(Modele):
    """Champs portés par toute réponse JSON : `mode` et, en mode enregistré, `enregistre_le`."""

    mode: Mode = Field(description="`direct` (appel Oriane de la requête) ou `enregistre` (cas rejoué).")
    enregistre_le: datetime | None = Field(
        default=None, description="Date d'enregistrement du cas rejoué ; obligatoire en mode enregistré."
    )

    @model_validator(mode="after")
    def _mode_coherent(self) -> Self:
        if self.mode == "enregistre" and self.enregistre_le is None:
            raise ValueError("en mode enregistre, enregistre_le est obligatoire")
        if self.mode == "direct" and self.enregistre_le is not None:
            raise ValueError("en mode direct, enregistre_le reste vide")
        return self


class Erreur(Modele):
    """Enveloppe unique de toute erreur du service."""

    erreur: str = Field(
        description=(
            "Code `snake_case` : validation (422), introuvable (404), cle_demo_invalide (401), "
            "decision_manquante, version_non_tranchee, constat_manquant (409), non_implemente (501), "
            "oriane_injoignable, credits_epuises (503)."
        )
    )
    detail: str = Field(description="Phrase lisible, à afficher telle quelle.")
    mode: Mode


class Segment(Modele):
    """Morceau de texte typé : `libelle` (écrit par le service, filtré) ou `citation` (rapportée)."""

    type: Literal["libelle", "citation"]
    texte: str

    @model_validator(mode="after")
    def _filtrer_libelle(self) -> Self:
        if self.type == "libelle":
            mot = contient_libelle_refuse(self.texte)
            if mot is not None:
                raise ValueError(f"libellé refusé dans un segment libelle : {mot}")
        return self


# --- video.v1 ----------------------------------------------------------------------------------


class Transcription(Modele):
    """Transcription de la parole, lue chez Oriane au niveau `default`, jamais refaite."""

    texte: str
    source: Literal["Oriane"] = SOURCE_ORIANE
    niveau: Literal["default"] = NIVEAU_DEFAULT
    lue_le: datetime


class TexteEcran(Modele):
    """Texte affiché à l'écran de la vidéo, lu chez Oriane."""

    texte: str
    source: Literal["Oriane"] = SOURCE_ORIANE
    lue_le: datetime


class Apercu(Modele):
    """Vignette et images clés de la vidéo, adresses relayées telles que servies par Oriane."""

    vignette: AdresseHttps | None = Field(default=None, description="Adresse de la vignette, si servie.")
    images_cles: list[AdresseHttps] = Field(
        default_factory=list,
        max_length=LIMITE_IMAGES_CLES,
        description="Adresses des images clés, dix au plus.",
    )
    source: Literal["Oriane"] = SOURCE_ORIANE
    lue_le: datetime


class Video(Reponse):
    """Vidéo `video.v1` : seuls les champs de la liste blanche, sans aucune donnée de tiers."""

    identifiant: TexteNonVide
    plateforme: Plateforme
    identifiant_plateforme: TexteNonVide
    compte: TexteNonVide
    publie_le: datetime
    vues_selon_oriane: Compte | None = None
    interactions_selon_oriane: Compte | None = None
    legende: str = ""
    requetes_trouvees: list[str] = Field(default_factory=list)
    transcription: Transcription
    texte_ecran: TexteEcran
    lien: TexteNonVide
    apercu: Apercu | None = Field(
        default=None, description="Aperçu relayé par Oriane ; absent quand Oriane n'en sert aucun."
    )


# --- mesure et recit.v1 ------------------------------------------------------------------------


class Fenetre(Modele):
    """Fenêtre de temps sur laquelle porte une mesure (bornes comprises)."""

    debut: datetime
    fin: datetime

    @model_validator(mode="after")
    def _ordonnee(self) -> Self:
        if self.fin < self.debut:
            raise ValueError("la fin de la fenêtre précède son début")
        return self


class Echantillon(Modele):
    """Ce qui a été consulté pour calculer une mesure."""

    resultats_consultes: Compte
    limite_page: Annotated[int, Field(ge=1)]
    tronque: bool


class Mesure(Modele):
    """Mesure chiffrée : jamais sans `methode` ni `fenetre` ; une valeur nulle dit sa raison."""

    nom: TexteNonVide
    valeur: int | float | None
    unite: str
    methode: TexteNonVide
    fenetre: Fenetre
    echantillon: Echantillon
    source: TexteNonVide
    raison: str | None = None

    @model_validator(mode="after")
    def _raison_si_nulle(self) -> Self:
        if self.valeur is None and not (self.raison or "").strip():
            raise ValueError("une mesure de valeur nulle dit sa raison")
        return self


class PlusAncienneVersion(Modele):
    """Plus ancienne version retrouvée dans les sources consultées (jamais « la première »)."""

    video: TexteNonVide
    publie_le: datetime
    libelle: Literal["plus ancienne version retrouvée dans les sources consultées"] = (
        LIBELLE_PLUS_ANCIENNE_VERSION
    )


class Recit(Reponse):
    """Récit `recit.v1` : une phrase surveillée, ses vidéos, ses mesures et ce qui n'a pas été cherché."""

    identifiant: TexteNonVide
    phrase_surveillee: TexteNonVide = Field(description="Citation exacte, jamais filtrée.")
    requete_en_clair: TexteNonVide = Field(description="Requête envoyée à Oriane, lisible.")
    videos: list[str] = Field(default_factory=list)
    mesures: list[Mesure] = Field(default_factory=list)
    plus_ancienne_version: PlusAncienneVersion | None = None
    non_cherche: list[Segment] = Field(default_factory=list)
    calcule_le: datetime


class CoutActualisation(Modele):
    """Coût estimé d'une actualisation, affiché avant le geste."""

    credits_estimes: Compte
    methode: TexteNonVide


class Radar(Reponse):
    """Radar des récits : les récits calculés, la date du calcul et le coût d'une actualisation."""

    recits: list[Recit] = Field(default_factory=list)
    calcule_le: datetime
    raison: str | None = Field(default=None, description="Pourquoi ce mode, en clair.")
    cout_actualisation: CoutActualisation | None = None


# --- ecart.v1 ----------------------------------------------------------------------------------


class Operation(Modele):
    """Opération d'édition au mot entre la source et la reprise (positions comptées dès 0)."""

    type: TypeOperation
    position_source: Position
    position_reprise: Position
    mots_source: list[str] = Field(default_factory=list)
    mots_reprise: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _mots_coherents(self) -> Self:
        attendus = {
            "retire": (True, False),
            "ajoute": (False, True),
            "remplace": (True, True),
        }[self.type]
        if (bool(self.mots_source), bool(self.mots_reprise)) != attendus:
            raise ValueError(f"mots incohérents pour une opération {self.type}")
        return self


class AttributionTranscription(Modele):
    """Attribution d'une transcription comparée : toujours Oriane, avec l'heure de lecture."""

    source: Literal["Oriane"] = SOURCE_ORIANE
    niveau: Literal["default"] = NIVEAU_DEFAULT
    lue_le: datetime


class TranscriptionsComparees(Modele):
    """Attribution des deux transcriptions comparées."""

    source: AttributionTranscription
    reprise: AttributionTranscription


class HeureDansLaVideo(Modele):
    """Heure du passage dans la vidéo : non fournie par Oriane au niveau `default`."""

    secondes: float | None = None
    libelle: str = LIBELLE_HEURE_NON_FOURNIE


class Ecart(Reponse):
    """Écart `ecart.v1` entre deux versions, au mot, sans aucune qualification de l'écart."""

    identifiant: TexteNonVide
    video_source: TexteNonVide
    video_reprise: TexteNonVide
    operations: list[Operation] = Field(default_factory=list)
    ecart_legende: list[Operation] = Field(default_factory=list)
    ecart_texte_ecran: list[Operation] = Field(default_factory=list)
    normalisation: Literal["mots.v1"] = Field(
        default=NORMALISATION_MOTS_V1,
        description=(
            "Normalisation mots.v1 : forme Unicode composée (NFC) et minuscules, ponctuation supprimée "
            "sauf la virgule ou le point entre deux chiffres (séparateur décimal), apostrophe et trait "
            "d'union changés en espace, accents et nombres gardés tels que transcrits, découpage sur "
            "les espaces."
        ),
    )
    transcriptions: TranscriptionsComparees
    heure_dans_la_video: HeureDansLaVideo = Field(default_factory=HeureDansLaVideo)


# --- decision.v1 et fiche.v1 -------------------------------------------------------------------


class Decision(Modele):
    """Décision `decision.v1` : l'une des trois, prise par une personne, avec son rôle et l'heure."""

    valeur: ValeurDecision
    role: TexteNonVide
    note: str = ""
    heure: datetime


class VersionFiche(Modele):
    """Une des deux versions de la fiche, à trancher par le journaliste."""

    video: TexteNonVide
    lien: TexteNonVide
    compte: TexteNonVide
    date: datetime
    vues_selon_oriane: Compte | None = None
    etat: EtatVersion = "a_trancher"
    note: str = ""


class Resume(Modele):
    """Résumé de la fiche, en segments, avec sa méthode de rédaction."""

    segments: list[Segment] = Field(default_factory=list)
    methode: TexteNonVide = METHODE_GABARIT_V1


class GesteFiche(Modele):
    """Ligne du journal de la fiche : un geste, son heure."""

    heure: datetime
    geste: TexteNonVide
    detail: str = ""


class Fiche(Reponse):
    """Fiche de vérification `fiche.v1` : sources, indices, limites, constat et décision humaine."""

    identifiant: TexteNonVide
    comparaison: TexteNonVide
    requete: str
    versions: list[VersionFiche] = Field(min_length=2, max_length=2)
    indices_de_transformation: list[Segment] = Field(default_factory=list)
    plus_ancienne_version: PlusAncienneVersion | None = None
    non_cherche: list[Segment] = Field(default_factory=list)
    limites: list[Segment]
    resume: Resume
    constat: str = Field(
        default="", description="Écrit par le journaliste, vide à la création, jamais filtré."
    )
    decision: Decision | None = None
    journal: list[GesteFiche] = Field(default_factory=list)

    @field_validator("limites")
    @classmethod
    def _limite_transcriptions(cls, limites: list[Segment]) -> list[Segment]:
        if not any(s.type == "libelle" and s.texte == LIMITE_TRANSCRIPTIONS for s in limites):
            raise ValueError(f"les limites disent : « {LIMITE_TRANSCRIPTIONS} »")
        return limites


# --- corps de requête --------------------------------------------------------------------------


class DemandeComparaison(Modele):
    """Corps de `POST /v1/comparaisons` : deux vidéos du cas, la source puis la reprise."""

    video_source: TexteNonVide
    video_reprise: TexteNonVide

    @model_validator(mode="after")
    def _distinctes(self) -> Self:
        if self.video_source == self.video_reprise:
            raise ValueError("la source et la reprise sont deux vidéos distinctes")
        return self


class DemandeFiche(Modele):
    """Corps de `POST /v1/fiches` : la comparaison dont la fiche part."""

    comparaison: TexteNonVide


class VersionTranchee(Modele):
    """Geste du journaliste sur une version de la fiche."""

    video: TexteNonVide
    etat: EtatVersion
    note: str = ""


class ModificationFiche(Modele):
    """Corps de `PATCH /v1/fiches/{id}` : versions tranchées et constat, chacun facultatif."""

    versions: list[VersionTranchee] | None = None
    constat: str | None = None


class DemandeDecision(Modele):
    """Corps de `POST /v1/fiches/{id}/decision` ; l'heure est posée par le service."""

    valeur: ValeurDecision
    role: TexteNonVide
    note: str = ""


# --- état et journal ---------------------------------------------------------------------------


class Etat(Modele):
    """État du service pour la barre d'état des écrans."""

    mode: Mode
    raison: str
    enregistre_le: datetime | None = Field(default=None, description="Date du cas rejoué, s'il y en a un.")
    credits_du_jour: Compte
    plafond_credits_jour: Compte
    version: TexteNonVide
    contrat: Literal["api.v1"] = API_V1


class EntreeJournal(Modele):
    """Ligne du journal des appels (jamais de réponse brute ni de clé)."""

    id: int
    heure: datetime
    route: str
    cible: str | None = None
    filtres: Any = None
    projection: Any = None
    resultats: Any = None
    credits_estimes: float | None = None
    duree_ms: float | None = None
    code: int | None = None
    mode: str | None = None


class Journal(Reponse):
    """Journal des appels, le plus récent d'abord."""

    entrees: list[EntreeJournal] = Field(default_factory=list)


# --- contrats exportés -------------------------------------------------------------------------

CONTRATS: dict[str, type[Modele]] = {
    VIDEO_V1: Video,
    RECIT_V1: Recit,
    ECART_V1: Ecart,
    FICHE_V1: Fiche,
    DECISION_V1: Decision,
}


def schema_contrat(nom: str) -> dict[str, Any]:
    """JSON Schema du contrat nommé (`video.v1`, …), tel qu'exporté dans `contrats/`."""
    schema = CONTRATS[nom].model_json_schema()
    return {"$id": nom, **schema}
