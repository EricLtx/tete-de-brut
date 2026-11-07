"""Configuration du service, construite uniquement depuis l'environnement (aucun secret dans le dépôt)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

RACINE_SERVICE = Path(__file__).resolve().parent.parent
BASE_PAR_DEFAUT = RACINE_SERVICE / "donnees" / "tete-de-brut.sqlite"
CAS_PAR_DEFAUT = RACINE_SERVICE / "cas"
MODES_DONNEES = ("auto", "enregistre")
ORIANE_URL_PAR_DEFAUT = "https://connect.oriane.xyz"
ORIANE_EN_TETE_PAR_DEFAUT = "Authorization"
ORIANE_PREFIXE_PAR_DEFAUT = "Bearer "
RESUME_MODES = ("gabarit", "modele")
MODELE_LANGUE_URL_PAR_DEFAUT = "https://api.anthropic.com"
MODELE_LANGUE_ID_PAR_DEFAUT = "claude-sonnet-5-5"


class ErreurConfiguration(ValueError):
    """Une variable d'environnement est invalide : le service refuse de démarrer."""


def _texte(env: Mapping[str, str], nom: str, defaut: str = "") -> str:
    """Lit une variable ; une valeur vide ou blanche vaut absente."""
    return env.get(nom, "").strip() or defaut


def _entier(env: Mapping[str, str], nom: str, defaut: int) -> int:
    brut = _texte(env, nom)
    if not brut:
        return defaut
    try:
        return int(brut)
    except ValueError as exc:
        raise ErreurConfiguration(f"{nom} doit être un entier") from exc


def _nombre(env: Mapping[str, str], nom: str, defaut: float) -> float:
    brut = _texte(env, nom)
    if not brut:
        return defaut
    try:
        return float(brut)
    except ValueError as exc:
        raise ErreurConfiguration(f"{nom} doit être un nombre") from exc


def _prefixe_auth(env: Mapping[str, str]) -> str:
    """Préfixe devant la clé Oriane : « Bearer » et une espace par défaut, `aucun` pour n'en poser aucun."""
    brut = _texte(env, "ORIANE_PREFIXE_AUTH")
    if not brut:
        return ORIANE_PREFIXE_PAR_DEFAUT
    return "" if brut.lower() == "aucun" else brut + " "


def _origines(brut: str) -> tuple[str, ...]:
    """Liste exacte d'origines séparées par des virgules ; l'origine `*` est refusée."""
    origines = tuple(o.strip().rstrip("/") for o in brut.split(",") if o.strip())
    if "*" in origines:
        raise ErreurConfiguration(
            "ORIGINES_AUTORISEES n'accepte pas l'origine * : lister les origines exactes"
        )
    return origines


@dataclass(frozen=True)
class Configuration:
    """Réglages du service. Les clés n'apparaissent jamais dans `repr`."""

    oriane_cle: str = field(default="", repr=False)
    oriane_url: str = ORIANE_URL_PAR_DEFAUT
    oriane_en_tete_auth: str = ORIANE_EN_TETE_PAR_DEFAUT
    oriane_prefixe_auth: str = ORIANE_PREFIXE_PAR_DEFAUT
    oriane_delai_s: float = 20.0
    origines_autorisees: tuple[str, ...] = ()
    cle_demo: str = field(default="", repr=False)
    mode_donnees: str = "auto"
    chemin_base: Path = BASE_PAR_DEFAUT
    chemin_cas: Path = CAS_PAR_DEFAUT
    plafond_credits_jour: int = 600
    bascule: str = ""  # raison d'une bascule en mode enregistré décidée à l'exécution (S04) ; vide, aucune
    port: int = 8080
    # Résumé de la fiche (S10, ADR-0002) : gabarit par défaut ; `modele` n'agit qu'avec une clé.
    resume_mode: str = "gabarit"
    modele_langue_url: str = MODELE_LANGUE_URL_PAR_DEFAUT
    modele_langue_cle: str = field(default="", repr=False)
    modele_langue_id: str = MODELE_LANGUE_ID_PAR_DEFAUT
    chemin_comptes: Path | None = None  # liste des comptes à écarter d'une recherche (S13), hors Git

    @classmethod
    def depuis_environnement(cls, environnement: Mapping[str, str] | None = None) -> Configuration:
        """Construit la configuration depuis `os.environ` (ou depuis le mapping fourni, pour les tests)."""
        env = os.environ if environnement is None else environnement
        mode_donnees = _texte(env, "MODE_DONNEES", "auto")
        if mode_donnees not in MODES_DONNEES:
            raise ErreurConfiguration("MODE_DONNEES vaut auto ou enregistre")
        resume_mode = _texte(env, "RESUME_MODE", "gabarit")
        if resume_mode not in RESUME_MODES:
            raise ErreurConfiguration("RESUME_MODE vaut gabarit ou modele")
        return cls(
            oriane_cle=_texte(env, "ORIANE_API_KEY"),
            oriane_url=_texte(env, "ORIANE_URL", ORIANE_URL_PAR_DEFAUT).rstrip("/"),
            oriane_en_tete_auth=_texte(env, "ORIANE_EN_TETE_AUTH", ORIANE_EN_TETE_PAR_DEFAUT),
            oriane_prefixe_auth=_prefixe_auth(env),
            oriane_delai_s=_nombre(env, "ORIANE_DELAI_S", 20.0),
            origines_autorisees=_origines(_texte(env, "ORIGINES_AUTORISEES")),
            cle_demo=_texte(env, "CLE_DEMO"),
            mode_donnees=mode_donnees,
            chemin_base=Path(_texte(env, "CHEMIN_BASE", str(BASE_PAR_DEFAUT))),
            chemin_cas=Path(_texte(env, "CHEMIN_CAS", str(CAS_PAR_DEFAUT))),
            plafond_credits_jour=_entier(env, "PLAFOND_CREDITS_JOUR", 600),
            port=_entier(env, "PORT", 8080),
            resume_mode=resume_mode,
            modele_langue_url=_texte(env, "MODELE_LANGUE_URL", MODELE_LANGUE_URL_PAR_DEFAUT).rstrip("/"),
            modele_langue_cle=_texte(env, "MODELE_LANGUE_API_KEY", _texte(env, "ANTHROPIC_API_KEY")),
            modele_langue_id=_texte(env, "MODELE_LANGUE_ID", MODELE_LANGUE_ID_PAR_DEFAUT),
            chemin_comptes=Path(_texte(env, "CHEMIN_COMPTES")) if _texte(env, "CHEMIN_COMPTES") else None,
        )

    @property
    def mode(self) -> str:
        """Mode effectif : `enregistre` sans clé Oriane, sur demande ou après bascule, sinon `direct`."""
        if not self.oriane_cle or self.mode_donnees == "enregistre" or self.bascule:
            return "enregistre"
        return "direct"

    @property
    def raison(self) -> str:
        """Pourquoi le mode effectif est celui-là, en clair."""
        if self.bascule:
            return self.bascule
        if not self.oriane_cle:
            return "ORIANE_API_KEY absente : le service rejoue le cas enregistré"
        if self.mode_donnees == "enregistre":
            return "MODE_DONNEES=enregistre : le service rejoue le cas enregistré"
        return "ORIANE_API_KEY présente : appels Oriane en direct"
