"""Fixtures communes à tous les mandats : configuration, application et clients de test.

Les noms sont stables : les mandats suivants (S02 à S10) les réutilisent sans les redéfinir.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Configuration
from app.main import creer_application

ORIGINE_LOVABLE = "https://exemple.lovable.app"
CLE_DEMO_TEST = "secret-de-test"


def construire_config(tmp_path: Path, **surcharges: str) -> Configuration:
    """Configuration de test : aucune clé Oriane, base temporaire, une seule origine déclarée."""
    environnement = {
        "CHEMIN_BASE": str(tmp_path / "tete-de-brut-test.sqlite"),
        "CHEMIN_CAS": str(tmp_path / "cas"),
        "ORIGINES_AUTORISEES": ORIGINE_LOVABLE,
    }
    environnement.update(surcharges)
    return Configuration.depuis_environnement(environnement)


@pytest.fixture
def config_test(tmp_path: Path) -> Configuration:
    """Configuration minimale sans clé Oriane, avec base temporaire (mode enregistré)."""
    return construire_config(tmp_path)


@pytest.fixture
def client(config_test: Configuration) -> Iterator[TestClient]:
    """Client de test sur l'application construite avec `config_test` (service ouvert)."""
    with TestClient(creer_application(config_test)) as c:
        yield c


@pytest.fixture
def client_avec_cle(tmp_path: Path) -> Iterator[TestClient]:
    """Client de test dont l'application exige la clé de démonstration `secret-de-test`."""
    config = construire_config(tmp_path, CLE_DEMO=CLE_DEMO_TEST)
    with TestClient(creer_application(config)) as c:
        yield c
