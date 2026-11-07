"""Fixtures communes à tous les mandats : configuration, application et clients de test.

Les noms sont stables : les mandats suivants (S02 à S10) les réutilisent sans les redéfinir.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import cas
from app.config import Configuration
from app.main import creer_application
from app.modeles import Video

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


# --- vidéos simulées (S02) : réutilisées par tous les mandats, jamais redéfinies -------------------
# Aucune donnée réelle : comptes, textes et liens sont fictifs et marqués « simulé ».

ENREGISTRE_LE_TEST = "2026-11-07T08:00:00+00:00"
LUE_LE_TEST = "2026-11-07T07:55:00+00:00"


def fabriquer_video(**surcharges: Any) -> Video:
    """Fabrique une `Video` simulée valide (mode enregistré) ; chaque champ peut être surchargé."""
    donnees: dict[str, Any] = {
        "identifiant": "video-simulee-1",
        "plateforme": "tiktok",
        "identifiant_plateforme": "7000000000000000001",
        "compte": "compte_simule_1",
        "publie_le": "2026-11-05T09:00:00+00:00",
        "vues_selon_oriane": 12000,
        "interactions_selon_oriane": 800,
        "legende": "Légende simulée",
        "requetes_trouvees": ["phrase simulée"],
        "transcription": {
            "texte": "Propos simulé : phrase simulée pour les tests",
            "source": "Oriane",
            "niveau": "default",
            "lue_le": LUE_LE_TEST,
        },
        "texte_ecran": {"texte": "TEXTE À L'ÉCRAN SIMULÉ", "source": "Oriane", "lue_le": LUE_LE_TEST},
        "lien": "https://www.tiktok.com/@compte_simule_1/video/7000000000000000001",
        "mode": "enregistre",
        "enregistre_le": ENREGISTRE_LE_TEST,
    }
    donnees.update(surcharges)
    return Video.model_validate(donnees)


@pytest.fixture
def video_simulee() -> Callable[..., Video]:
    """Fabrique de vidéos simulées : `video_simulee(identifiant="v2", compte="…")`."""
    return fabriquer_video


@pytest.fixture
def deux_videos_comparables() -> tuple[Video, Video]:
    """Source et reprise d'un même propos simulé : la reprise retire « si l'État paie »."""
    source = fabriquer_video(
        identifiant="video-simulee-source",
        identifiant_plateforme="7000000000000000010",
        compte="compte_simule_source",
        publie_le="2026-11-04T08:00:00+00:00",
        legende="Légende simulée de la source",
        transcription={
            "texte": "Propos simulé : il faut dix mille postes si l'État paie",
            "lue_le": LUE_LE_TEST,
        },
        texte_ecran={"texte": "TEXTE SIMULÉ : 10 000 postes", "lue_le": LUE_LE_TEST},
        lien="https://www.tiktok.com/@compte_simule_source/video/7000000000000000010",
    )
    reprise = fabriquer_video(
        identifiant="video-simulee-reprise",
        plateforme="instagram",
        identifiant_plateforme="CSIMULEREPRISE",
        compte="compte_simule_reprise",
        publie_le="2026-11-06T18:00:00+00:00",
        vues_selon_oriane=90000,
        interactions_selon_oriane=5000,
        legende="Légende simulée de la reprise",
        transcription={"texte": "Propos simulé : il faut dix mille postes", "lue_le": LUE_LE_TEST},
        texte_ecran={"texte": "TEXTE SIMULÉ : dix mille postes", "lue_le": LUE_LE_TEST},
        lien="https://www.instagram.com/reel/CSIMULEREPRISE/",
    )
    return source, reprise


@pytest.fixture
def comparaison_simulee(client: TestClient, deux_videos_comparables: tuple[Video, Video]) -> dict[str, Any]:
    """Comparaison `ecart.v1` (S07) des deux vidéos comparables, posées en base puis comparées par la route.

    Rend le JSON de la comparaison ; les deux vidéos restent en base pour la fiche (S08).
    """
    from app import base

    for video in deux_videos_comparables:
        base.ecrire("video", video.identifiant, "video.v1", video.model_dump(mode="json"))
    source, reprise = deux_videos_comparables
    reponse = client.post(
        "/v1/comparaisons", json={"video_source": source.identifiant, "video_reprise": reprise.identifiant}
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


# Champs de tiers d'une réponse Oriane (relevé du 06/11) : aucun ne doit entrer en base ni au journal.
CHAMPS_TIERS_ORIANE = (
    "popularComments",
    "locationPlatformId",
    "locationCompleteAddress",
    "locationLatitude",
    "locationLongitude",
    "profileLocationPlatformId",
    "profileLocationCompleteAddress",
    "profileLocationLatitude",
    "profileLocationLongitude",
    "profilePictureUrl",
    "profileBio",
    "profileDisplayName",
    "mentions",
    "coAuthors",
    "audioAuthor",
)
CHAMPS_TIERS_MEDIA_ORIANE = ("tags", "transcriptChunks")

_REPONSE_ORIANE_SIMULEE: dict[str, Any] = {
    "metadata": {
        "requestId": "req_SIMULE0000000000000000000000001",
        "executionTime": 17,
        "timestamp": 1793952000000,
        "pagination": {"offset": 0, "limit": 100, "totalCount": 2},
    },
    "data": {
        "aggregations": {"totalViewsCount": 102000, "totalInteractionsCount": 5800},
        "results": [
            {
                "id": "cnt_SIMULE0000000000000000000001",
                "platform": "tiktok",
                "platformId": "7000000000000000010",
                "profileHandle": "compte_simule_source",
                "publishedAt": "2026-11-04T08:00:00.000Z",
                "viewsCount": 12000,
                "interactionsCount": 800,
                "caption": "Légende simulée de la source",
                "matchedQueries": ["dit:dix mille postes", "dit_ou_ecrit", "tete-de-brut-recherche"],
                "audioPlatformId": "audio-simule-1",
                "media": [
                    {
                        "type": "video",
                        "duration": 31.5,
                        "caption": "Légende simulée de la source",
                        "transcript": "Propos simulé : il faut dix mille postes si l'État paie",
                        "onScreenText": ["TEXTE SIMULÉ : 10 000 postes"],
                        "tags": [{"handle": "compte_tiers_simule", "x": 0.4, "y": 0.6}],
                        "frames": [{"url": "https://exemple.invalid/image-simulee.jpg"}],
                        "transcriptChunks": [{"start": 0, "end": 3, "text": "Propos simulé"}],
                    }
                ],
                "popularComments": [{"text": "commentaire simulé d'un tiers", "author": "tiers_simule"}],
                "locationPlatformId": "lieu-simule",
                "locationCompleteAddress": "1 rue Simulée, Ville Fictive",
                "locationLatitude": 0.0,
                "locationLongitude": 0.0,
                "profileLocationPlatformId": "lieu-profil-simule",
                "profileLocationCompleteAddress": "Ville Fictive",
                "profileLocationLatitude": 0.0,
                "profileLocationLongitude": 0.0,
                "profilePictureUrl": "https://exemple.invalid/photo-simulee.jpg",
                "profileBio": "Biographie simulée",
                "profileDisplayName": "Nom Affiché Simulé",
                "mentions": [{"handle": "compte_mentionne_simule"}],
                "coAuthors": [{"handle": "coauteur_simule"}],
                "audioAuthor": "auteur_audio_simule",
                "thumbnailMediaUrl": "https://exemple.invalid/vignette-simulee.jpg",
            },
            {
                "id": "cnt_SIMULE0000000000000000000002",
                "platform": "instagram",
                "platformId": "CSIMULEREPRISE",
                "profileHandle": "compte_simule_reprise",
                "publishedAt": "2026-11-06T18:00:00.000Z",
                "viewsCount": 90000,
                "interactionsCount": 5000,
                "caption": "Légende simulée de la reprise",
                "matchedQueries": [
                    "dit:dix mille postes",
                    "ecrit:dix mille postes",
                    "dit_ou_ecrit",
                    "tete-de-brut-recherche",
                ],
                "media": [
                    {
                        "type": "video",
                        "duration": 12.0,
                        "caption": "Légende simulée de la reprise",
                        "transcript": "Propos simulé : il faut dix mille postes",
                        "onScreenText": ["TEXTE SIMULÉ : dix mille postes"],
                        "tags": [],
                    }
                ],
                "popularComments": [],
                "profilePictureUrl": "https://exemple.invalid/photo-simulee-2.jpg",
                "profileBio": "Biographie simulée 2",
                "profileDisplayName": "Autre Nom Simulé",
                "mentions": [],
                "coAuthors": [],
                "audioAuthor": "auteur_audio_simule_2",
                "thumbnailMediaUrl": "https://exemple.invalid/vignette-simulee-2.jpg",
            },
        ],
    },
}


@pytest.fixture
def reponse_oriane_simulee() -> dict[str, Any]:
    """Réponse Oriane simulée (`/rest/contents/search`, niveau `default`), avec des champs de tiers.

    Forme d'après la spécification OpenAPI d'Oriane (`metadata`, `data.results[]`, `media[]`) ;
    copie neuve à chaque test, valeurs fictives évidentes, aucun nom réel.
    """
    return copy.deepcopy(_REPONSE_ORIANE_SIMULEE)


@pytest.fixture
def transport_oriane_simule(reponse_oriane_simulee: dict[str, Any]) -> Callable[..., httpx.MockTransport]:
    """Fabrique un `httpx.MockTransport` qui joue Oriane, sans réseau.

    `transport_oriane_simule(statut=200, corps=None, exception=None)` : par défaut la réponse simulée en 200 ;
    `corps` remplace le JSON rendu ; `exception` est levée à la place d'une réponse (expiration, coupure).
    Le transport garde les requêtes reçues dans `transport.requetes` (méthode, adresse, en-têtes, corps).
    """

    def fabriquer(
        statut: int = 200, corps: Any = None, exception: Exception | None = None
    ) -> httpx.MockTransport:
        requetes: list[httpx.Request] = []

        def repondre(requete: httpx.Request) -> httpx.Response:
            requete.read()
            requetes.append(requete)
            if exception is not None:
                raise exception
            contenu = reponse_oriane_simulee if corps is None else corps
            return httpx.Response(
                statut, content=json.dumps(contenu), headers={"content-type": "application/json"}
            )

        transport = httpx.MockTransport(repondre)
        transport.requetes = requetes  # type: ignore[attr-defined]
        return transport

    return fabriquer


# --- cas enregistré simulé (S04) -----------------------------------------------------------------

CAS_ENREGISTRE_LE = datetime(2026, 11, 6, 20, 0, tzinfo=UTC)
CAS_PHRASE = "dix mille postes"


@pytest.fixture
def cas_simule() -> Callable[..., Path]:
    """Fabrique le fichier du cas simulé dans `config.chemin_cas` : `cas_simule(config)` rend son chemin.

    Deux vidéos fictives dont les identifiants sont ceux de `reponse_oriane_simulee`, une phrase de trois
    mots (RG-02), mode `enregistre` ; aucune donnée réelle.
    """

    def ecrire(config: Configuration, phrases: tuple[str, ...] = (CAS_PHRASE,)) -> Path:
        videos = [
            fabriquer_video(
                identifiant=f"cnt_SIMULE000000000000000000000{i}",
                identifiant_plateforme=f"70000000000000000{i}0",
                compte=f"compte_simule_{i}",
                publie_le=f"2026-11-0{3 + i}T08:00:00+00:00",
                requetes_trouvees=list(phrases),
                lien=f"https://www.tiktok.com/@compte_simule_{i}/video/70000000000000000{i}0",
            )
            for i in (1, 2)
        ]
        document = cas.construire_document(
            enregistre_le=CAS_ENREGISTRE_LE,
            phrases=phrases,
            comptes=[],
            plateformes=[],
            fenetre=None,
            credits_estimes=15,
            videos=videos,
        )
        chemin = cas.fichier_cas(config)
        cas.ecrire_fichier(chemin, document)
        return chemin

    return ecrire
