"""F030 : la base SQLite est en WAL, les lectures n'attendent pas un écrivain, le schéma se crée une fois."""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from app import base


@pytest.fixture
def chemin_base(tmp_path: Path) -> Iterator[Path]:
    """Base temporaire, courante le temps du test ; le chemin précédent est rétabli ensuite."""
    precedent = base._chemin_courant
    chemin = tmp_path / "base-wal.sqlite"
    base.configurer(chemin)
    base.initialiser()
    yield chemin
    base.configurer(precedent)


def test_journal_en_wal(chemin_base: Path) -> None:
    with closing(sqlite3.connect(chemin_base)) as connexion:
        assert connexion.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_lecture_pendant_une_ecriture_ouverte(chemin_base: Path) -> None:
    """Un écrivain tient sa transaction dans un fil ; une lecture d'une autre connexion n'attend pas."""
    base.ecrire("video", "v1", "video.v1", {"titre": "avant"})
    ecriture_ouverte = threading.Event()
    liberer = threading.Event()
    erreurs: list[BaseException] = []

    def ecrivain() -> None:
        try:
            with base.transaction() as t:
                t.ecrire("video", "v2", "video.v1", {"titre": "en cours"})
                ecriture_ouverte.set()
                liberer.wait(timeout=30)
        except BaseException as exc:  # noqa: BLE001 - remonté à l'assertion du test
            erreurs.append(exc)
            ecriture_ouverte.set()

    fil = threading.Thread(target=ecrivain)
    fil.start()
    try:
        assert ecriture_ouverte.wait(timeout=10)
        debut = time.monotonic()
        lu = base.lire("video", "v1")
        liste = base.lister("video")
        journal = base.lire_journal()
        duree = time.monotonic() - debut
        assert lu == {"titre": "avant"}
        assert liste == [{"titre": "avant"}]  # l'écriture non validée reste invisible
        assert isinstance(journal, list)
        assert duree < 2, f"lecture bloquée {duree:.1f} s par une écriture ouverte"
    finally:
        liberer.set()
        fil.join(timeout=30)
    assert not erreurs
    assert {d["titre"] for d in base.lister("video")} == {"avant", "en cours"}


def test_ecriture_reste_exclusive(chemin_base: Path) -> None:
    """Une seconde écriture attend la première (BEGIN IMMEDIATE) : la sémantique de F023 est intacte."""
    with base.transaction() as t:
        t.ecrire("video", "v1", "video.v1", {"n": 1})
        with closing(sqlite3.connect(chemin_base, isolation_level=None, timeout=0)) as autre:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                autre.execute("BEGIN IMMEDIATE")


def test_transaction_annulee_en_cas_d_erreur(chemin_base: Path) -> None:
    base.ecrire("video", "v1", "video.v1", {"n": 1})
    with pytest.raises(RuntimeError):
        with base.transaction() as t:
            t.supprimer("video", "v1")
            raise RuntimeError("échec après suppression")
    assert base.lire("video", "v1") == {"n": 1}


def test_schema_cree_une_seule_fois(chemin_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appels: list[Path] = []
    origine = base._creer_schema
    monkeypatch.setattr(base, "_creer_schema", lambda cible: (appels.append(cible), origine(cible))[1])
    base._schemas_prets.discard(chemin_base)
    for i in range(5):
        base.ecrire("video", f"v{i}", "video.v1", {"n": i})
        base.lire("video", f"v{i}")
        base.lister("video")
        base.consigner(route="essai")
        base.lire_journal()
    assert len(appels) == 1


def test_base_supprimee_est_recreee(tmp_path: Path) -> None:
    precedent = base._chemin_courant
    chemin = tmp_path / "ephemere.sqlite"
    base.configurer(chemin)
    try:
        base.ecrire("video", "v1", "video.v1", {"n": 1})
        for fichier in tmp_path.glob("ephemere.sqlite*"):
            fichier.unlink()
        assert base.lire("video", "v1") is None
    finally:
        base.configurer(precedent)
