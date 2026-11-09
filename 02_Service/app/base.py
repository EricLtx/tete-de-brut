"""Magasin SQLite générique (bibliothèque standard) : documents versionnés et journal des appels.

Les autres modules s'en servent sans le modifier. Le journal ne reçoit jamais de réponse brute
ni de clé : `consigner` lève une erreur dès qu'on lui en présente une.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import BASE_PAR_DEFAUT

CHAMPS_JOURNAL = (
    "heure",
    "route",
    "cible",
    "filtres",
    "projection",
    "resultats",
    "credits_estimes",
    "duree_ms",
    "code",
    "mode",
)
CHAMPS_JSON = ("filtres", "projection", "resultats")
VARIABLES_SECRETES = ("ORIANE_API_KEY", "CLE_DEMO", "MODELE_LANGUE_API_KEY", "ANTHROPIC_API_KEY")
# Nom de champ ou motif de valeur qui trahit une clé d'accès.
NOM_SECRET = re.compile(r"(api[_-]?key|apikey|authorization|bearer|token|secret|cle[_-]?demo)", re.I)
VALEUR_SECRETE = re.compile(
    r"(bearer\s+\S|(api[_-]?key|apikey|token|secret|authorization)\s*[=:]\s*\S)", re.I
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    type TEXT NOT NULL,
    identifiant TEXT NOT NULL,
    version_contrat TEXT NOT NULL,
    json TEXT NOT NULL,
    cree_le TEXT NOT NULL,
    PRIMARY KEY (type, identifiant)
);
CREATE TABLE IF NOT EXISTS journal_appels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heure TEXT NOT NULL,
    route TEXT NOT NULL,
    cible TEXT,
    filtres TEXT,
    projection TEXT,
    resultats TEXT,
    credits_estimes REAL,
    duree_ms REAL,
    code INTEGER,
    mode TEXT
);
"""

_chemin_courant: Path = BASE_PAR_DEFAUT


class ErreurJournal(ValueError):
    """Une écriture au journal a été refusée (réponse brute ou clé)."""


def configurer(chemin: str | Path) -> None:
    """Fixe le fichier SQLite utilisé par défaut par les fonctions de ce module."""
    global _chemin_courant
    _chemin_courant = Path(chemin)


def maintenant() -> str:
    """Heure UTC au format ISO 8601, à la seconde."""
    return datetime.now(UTC).isoformat(timespec="seconds")


DELAI_VERROU_MS = 5000

_schemas_prets: set[Path] = set()
_verrou_schemas = threading.Lock()


def _ouvrir(cible: Path) -> sqlite3.Connection:
    """Ouvre une connexion : transactions gérées à la main, attente bornée si le fichier est occupé."""
    connexion = sqlite3.connect(cible, isolation_level=None, check_same_thread=False)
    connexion.row_factory = sqlite3.Row
    connexion.execute(f"PRAGMA busy_timeout = {DELAI_VERROU_MS}")
    return connexion


def _creer_schema(cible: Path) -> None:
    """Passe le fichier en WAL (mode durable, propre au fichier) et crée les tables absentes."""
    with closing(_ouvrir(cible)) as connexion:
        mode = connexion.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise sqlite3.OperationalError(f"le mode WAL n'a pas pu être activé (mode obtenu : {mode})")
        connexion.executescript(_SCHEMA)


def _preparer(cible: Path) -> None:
    """Prépare le fichier une seule fois par processus (et de nouveau s'il a disparu)."""
    if cible in _schemas_prets and cible.exists():
        return
    with _verrou_schemas:
        if cible in _schemas_prets and cible.exists():
            return
        cible.parent.mkdir(parents=True, exist_ok=True)
        _creer_schema(cible)
        _schemas_prets.add(cible)


@contextmanager
def _transaction(chemin: str | Path | None = None, *, ecriture: bool = True) -> Iterator[sqlite3.Connection]:
    """Ouvre une connexion pour un appel, dans une transaction explicite (validée ou annulée).

    Une écriture prend le verrou d'écriture dès l'ouverture (`BEGIN IMMEDIATE`) ; une lecture ouvre une
    transaction différée : en WAL, elle lit un instantané cohérent sans jamais attendre un écrivain.
    """
    cible = Path(chemin) if chemin is not None else _chemin_courant
    _preparer(cible)
    with closing(_ouvrir(cible)) as connexion:
        connexion.execute("BEGIN IMMEDIATE" if ecriture else "BEGIN")
        try:
            yield connexion
        except BaseException:
            connexion.execute("ROLLBACK")
            raise
        else:
            connexion.execute("COMMIT")


class Transaction:
    """Lectures et écritures d'une même transaction : tout est validé ensemble, ou rien ne l'est."""

    def __init__(self, connexion: sqlite3.Connection) -> None:
        self._connexion = connexion

    def ecrire(self, type: str, identifiant: str, version_contrat: str, objet: Any) -> None:
        """Enregistre (ou remplace) un document JSON identifié par (type, identifiant)."""
        self._connexion.execute(
            "INSERT OR REPLACE INTO documents (type, identifiant, version_contrat, json, cree_le)"
            " VALUES (?, ?, ?, ?, ?)",
            (type, identifiant, version_contrat, json.dumps(objet, ensure_ascii=False), maintenant()),
        )

    def supprimer(self, type: str, identifiant: str) -> bool:
        """Supprime le document (type, identifiant) ; rend vrai s'il existait."""
        curseur = self._connexion.execute(
            "DELETE FROM documents WHERE type = ? AND identifiant = ?", (type, identifiant)
        )
        return curseur.rowcount > 0

    def lister_avec_identifiants(self, type: str) -> list[tuple[str, Any]]:
        """Rend les documents d'un type avec leur identifiant, du plus ancien au plus récent."""
        lignes = self._connexion.execute(
            "SELECT identifiant, json FROM documents WHERE type = ? ORDER BY cree_le, identifiant", (type,)
        ).fetchall()
        return [(ligne["identifiant"], json.loads(ligne["json"])) for ligne in lignes]


@contextmanager
def transaction(chemin: str | Path | None = None) -> Iterator[Transaction]:
    """Une transaction pour plusieurs lectures et écritures de documents : une erreur les annule toutes.

    La transaction prend le verrou d'écriture dès son ouverture : aucune autre écriture ne s'intercale
    entre une lecture et l'écriture qui en dépend.
    """
    with _transaction(chemin) as connexion:
        yield Transaction(connexion)


def initialiser(chemin: str | Path | None = None) -> None:
    """Crée le dossier, le fichier, le mode WAL et les deux tables s'ils n'existent pas."""
    _preparer(Path(chemin) if chemin is not None else _chemin_courant)


def ecrire(
    type: str,
    identifiant: str,
    version_contrat: str,
    objet: Any,
    *,
    chemin: str | Path | None = None,
) -> None:
    """Enregistre (ou remplace) un document JSON identifié par (type, identifiant)."""
    with transaction(chemin) as t:
        t.ecrire(type, identifiant, version_contrat, objet)


def lire(type: str, identifiant: str, *, chemin: str | Path | None = None) -> Any | None:
    """Rend le document (objet JSON décodé), ou `None` s'il n'existe pas."""
    with _transaction(chemin, ecriture=False) as connexion:
        ligne = connexion.execute(
            "SELECT json FROM documents WHERE type = ? AND identifiant = ?", (type, identifiant)
        ).fetchone()
    return json.loads(ligne["json"]) if ligne else None


def purger(type: str, a_garder: set[str], *, chemin: str | Path | None = None) -> int:
    """Supprime les documents d'un type dont l'identifiant n'est pas dans `a_garder` ; rend leur nombre."""
    with _transaction(chemin) as connexion:
        lignes = connexion.execute("SELECT identifiant FROM documents WHERE type = ?", (type,)).fetchall()
        inutiles = [(type, ligne["identifiant"]) for ligne in lignes if ligne["identifiant"] not in a_garder]
        connexion.executemany("DELETE FROM documents WHERE type = ? AND identifiant = ?", inutiles)
    return len(inutiles)


def supprimer(type: str, identifiant: str, *, chemin: str | Path | None = None) -> bool:
    """Supprime le document (type, identifiant) ; rend vrai s'il existait."""
    with transaction(chemin) as t:
        return t.supprimer(type, identifiant)


def lister_avec_identifiants(type: str, *, chemin: str | Path | None = None) -> list[tuple[str, Any]]:
    """Rend les documents d'un type avec leur identifiant, du plus ancien au plus récent."""
    with transaction(chemin) as t:
        return t.lister_avec_identifiants(type)


def lister(type: str, *, chemin: str | Path | None = None) -> list[Any]:
    """Rend les documents d'un type, du plus ancien au plus récent."""
    with _transaction(chemin, ecriture=False) as connexion:
        lignes = connexion.execute(
            "SELECT json FROM documents WHERE type = ? ORDER BY cree_le, identifiant", (type,)
        ).fetchall()
    return [json.loads(ligne["json"]) for ligne in lignes]


def _contient_secret(valeur: Any) -> bool:
    """Vrai si la valeur (ou une clé de dictionnaire imbriqué) ressemble à une clé d'accès ou en est une."""
    if isinstance(valeur, dict):
        return any(NOM_SECRET.search(str(k)) or _contient_secret(v) for k, v in valeur.items())
    if isinstance(valeur, list | tuple | set):
        return any(_contient_secret(v) for v in valeur)
    if isinstance(valeur, str):
        connus = [os.environ.get(nom, "") for nom in VARIABLES_SECRETES]
        return bool(VALEUR_SECRETE.search(valeur)) or any(c and len(c) >= 4 and c in valeur for c in connus)
    return False


def consigner(**champs: Any) -> int:
    """Ajoute une ligne au journal des appels et rend son identifiant.

    Refuse tout champ inconnu, tout champ `reponse` (une réponse brute n'entre jamais au journal)
    et toute valeur qui contient une clé. `route` est obligatoire ; `heure` est posée si absente.
    """
    if "reponse" in champs:
        raise ErreurJournal("le journal refuse le champ reponse : pas de réponse brute au journal")
    inconnus = sorted(set(champs) - set(CHAMPS_JOURNAL))
    if inconnus:
        raise ErreurJournal(f"champ inconnu au journal : {', '.join(inconnus)}")
    if not champs.get("route"):
        raise ErreurJournal("le champ route est obligatoire")
    for nom, valeur in champs.items():
        if _contient_secret(valeur):
            raise ErreurJournal(f"le champ {nom} contient une clé : refusé")
    ligne = {nom: champs.get(nom) for nom in CHAMPS_JOURNAL}
    ligne["heure"] = ligne["heure"] or maintenant()
    for nom in CHAMPS_JSON:
        if ligne[nom] is not None and not isinstance(ligne[nom], str):
            ligne[nom] = json.dumps(ligne[nom], ensure_ascii=False)
    with _transaction() as connexion:
        curseur = connexion.execute(
            f"INSERT INTO journal_appels ({', '.join(CHAMPS_JOURNAL)})"
            f" VALUES ({', '.join('?' for _ in CHAMPS_JOURNAL)})",
            tuple(ligne[nom] for nom in CHAMPS_JOURNAL),
        )
        return int(curseur.lastrowid)


def lire_journal(limite: int = 100) -> list[dict[str, Any]]:
    """Rend les dernières lignes du journal, la plus récente d'abord."""
    with _transaction(ecriture=False) as connexion:
        lignes = connexion.execute(
            "SELECT id, " + ", ".join(CHAMPS_JOURNAL) + " FROM journal_appels ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    resultat = []
    for ligne in lignes:
        entree = dict(ligne)
        for nom in CHAMPS_JSON:
            if entree[nom] is not None:
                try:
                    entree[nom] = json.loads(entree[nom])
                except json.JSONDecodeError:
                    pass
        resultat.append(entree)
    return resultat
