"""Adaptateur Oriane (S03) : requête, erreurs, liste blanche, journal, `GET /v1/videos/{id}`.

Aucun réseau : `httpx.MockTransport` joue Oriane. Seul le test marqué `reel` appelle le vrai service.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import base, liste_blanche
from app.config import Configuration
from app.main import creer_application
from app.modeles import Fenetre, Video
from app.oriane import (
    CreditsEpuises,
    OrianeInjoignable,
    RequeteInvalide,
    construire_corps,
    rechercher,
)
from tests.conftest import (
    CHAMPS_TIERS_MEDIA_ORIANE,
    CHAMPS_TIERS_ORIANE,
    construire_config,
)

CLE_TEST = "cle-fictive-pour-les-tests-0001"
FENETRE = Fenetre(
    debut=datetime(2026, 11, 1, 0, 0, tzinfo=UTC),
    fin=datetime(2026, 11, 7, 23, 59, tzinfo=UTC),
)
PHRASE = "dix mille postes"
RACINE_SERVICE = Path(__file__).resolve().parent.parent


@pytest.fixture
def config_oriane(tmp_path: Path) -> Configuration:
    """Configuration avec une clé fictive : mode direct, base temporaire."""
    config = construire_config(tmp_path, ORIANE_API_KEY=CLE_TEST)
    base.configurer(config.chemin_base)
    base.initialiser()
    return config


def chercher(config: Configuration, transport: httpx.MockTransport, **options: Any):
    options.setdefault("fenetre", FENETRE)
    return asyncio.run(rechercher([PHRASE], config=config, transport=transport, **options))


def feuilles(valeur: Any, *, cles: bool = True) -> list[str]:
    """Toutes les chaînes d'un objet JSON (valeurs et, par défaut, noms de champs)."""
    if isinstance(valeur, dict):
        return [t for k, v in valeur.items() for t in [*([str(k)] if cles else []), *feuilles(v, cles=cles)]]
    if isinstance(valeur, list):
        return [t for v in valeur for t in feuilles(v, cles=cles)]
    return [valeur] if isinstance(valeur, str) else []


def valeurs_tiers(reponse: dict[str, Any]) -> set[str]:
    """Valeurs textuelles des champs de tiers servis par la réponse simulée."""
    trouvees: set[str] = set()
    for resultat in reponse["data"]["results"]:
        for nom in CHAMPS_TIERS_ORIANE:
            if nom in resultat:
                trouvees.update(t for t in feuilles(resultat[nom], cles=False) if len(t) > 3)
        for media in resultat["media"]:
            # `transcriptChunks` est exclu des valeurs : ses extraits recoupent la transcription autorisée.
            for nom in set(CHAMPS_TIERS_MEDIA_ORIANE) - {"transcriptChunks"}:
                if nom in media:
                    trouvees.update(t for t in feuilles(media[nom], cles=False) if len(t) > 3)
    return trouvees


# --- requête envoyée ---------------------------------------------------------------------------------


def enfant(origine: str, filtre: str, phrase: str) -> dict:
    return {
        "name": f"{origine}:{phrase}",
        "operator": "and",
        "filters": {filtre: {"includesExactly": {"values": [phrase], "operator": "or"}}},
    }


def test_corps_de_requete_exact():
    corps = construire_corps([PHRASE], ["compte_simule_source"], FENETRE, ["tiktok"])
    assert corps == {
        "name": "tete-de-brut-recherche",
        "operator": "and",
        "filters": {
            "profileHandle": {"exactMatch": ["compte_simule_source"]},
            "platform": {"includes": ["tiktok"]},
            "publishedAt": {"after": "2026-11-01", "before": "2026-11-07"},
        },
        "queries": [
            {
                "name": "dit_ou_ecrit",
                "operator": "or",
                "queries": [enfant("dit", "transcript", PHRASE), enfant("ecrit", "onScreenText", PHRASE)],
            }
        ],
    }
    assert "transcript" not in corps["filters"]
    assert "onScreenText" not in corps["filters"]


def test_deux_phrases_quatre_enfants_nommes():
    corps = construire_corps(["phrase A", " phrase B ", "phrase A"])
    assert corps["operator"] == "and"
    assert corps["filters"] == {}
    (union,) = corps["queries"]
    assert union["operator"] == "or"
    assert [q["name"] for q in union["queries"]] == [
        "dit:phrase A",
        "ecrit:phrase A",
        "dit:phrase B",
        "ecrit:phrase B",
    ]
    assert union["queries"][2] == enfant("dit", "transcript", "phrase B")
    assert union["queries"][3] == enfant("ecrit", "onScreenText", "phrase B")


def test_phrase_trop_longue_refusee(config_oriane, transport_oriane_simule):
    transport = transport_oriane_simule()
    assert construire_corps(["x" * 256])
    with pytest.raises(RequeteInvalide, match="256"):
        chercher_phrases(config_oriane, transport, ["x" * 257])
    assert transport.requetes == []


def chercher_phrases(config, transport, phrases):
    return asyncio.run(rechercher(phrases, config=config, transport=transport, fenetre=FENETRE))


def test_requetes_trouvees_sont_les_phrases(config_oriane, transport_oriane_simule, reponse_oriane_simulee):
    resultats = reponse_oriane_simulee["data"]["results"]
    resultats[0]["matchedQueries"] = ["ecrit:phrase B", "dit_ou_ecrit", "tete-de-brut-recherche"]
    resultats[1]["matchedQueries"] = [
        "dit:phrase A",
        "ecrit:phrase A",
        "dit_ou_ecrit",
        "tete-de-brut-recherche",
    ]
    transport = transport_oriane_simule(corps=reponse_oriane_simulee)
    resultat = chercher_phrases(config_oriane, transport, ["phrase A", "phrase B"])
    assert resultat.videos[0].requetes_trouvees == ["phrase B"]
    assert resultat.videos[1].requetes_trouvees == ["phrase A"]
    ligne = base.lire_journal()[0]
    assert ligne["resultats"]["dits"] == 1
    assert ligne["resultats"]["ecrits"] == 2
    assert ligne["resultats"]["sans_origine"] == 0


def test_requetes_trouvees_dans_l_ordre_des_phrases(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    reponse_oriane_simulee["data"]["results"][0]["matchedQueries"] = ["ecrit:phrase B", "dit:phrase A"]
    resultat = chercher_phrases(
        config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee), ["phrase A", "phrase B"]
    )
    assert resultat.videos[0].requetes_trouvees == ["phrase A", "phrase B"]


def test_sans_matched_queries_liste_vide_et_comptee(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    del reponse_oriane_simulee["data"]["results"][0]["matchedQueries"]
    resultat = chercher_phrases(
        config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee), [PHRASE]
    )
    assert resultat.videos[0].requetes_trouvees == []
    assert resultat.videos[1].requetes_trouvees == [PHRASE]
    assert base.lire_journal()[0]["resultats"]["sans_origine"] == 1


def test_requete_envoyee(config_oriane, transport_oriane_simule):
    transport = transport_oriane_simule()
    chercher(config_oriane, transport, comptes=["compte_simule_source"])
    (requete,) = transport.requetes
    assert requete.method == "POST"
    assert requete.url.host == "connect.oriane.xyz"
    assert requete.url.path == "/rest/contents/search"
    assert dict(requete.url.params) == {
        "sort": "publishedAt:asc",
        "offset": "0",
        "limit": "100",
        "projection": "default",
    }
    assert requete.headers["authorization"] == f"Bearer {CLE_TEST}"
    corps = json.loads(requete.content)
    assert corps == construire_corps([PHRASE], ["compte_simule_source"], FENETRE)
    assert corps["filters"]["profileHandle"] == {"exactMatch": ["compte_simule_source"]}
    assert corps["filters"]["publishedAt"] == {"after": "2026-11-01", "before": "2026-11-07"}


def test_en_tete_et_prefixe_viennent_de_la_configuration(tmp_path, transport_oriane_simule):
    config = construire_config(
        tmp_path,
        ORIANE_API_KEY=CLE_TEST,
        ORIANE_EN_TETE_AUTH="X-Acces-Simule",
        ORIANE_PREFIXE_AUTH="aucun",
        ORIANE_URL="https://oriane.exemple.invalid/",
    )
    base.configurer(config.chemin_base)
    transport = transport_oriane_simule()
    chercher(config, transport)
    (requete,) = transport.requetes
    assert requete.headers["x-acces-simule"] == CLE_TEST
    assert "authorization" not in requete.headers
    assert requete.url.host == "oriane.exemple.invalid"


def test_defauts_de_configuration(config_test):
    assert config_test.oriane_url == "https://connect.oriane.xyz"
    assert config_test.oriane_en_tete_auth == "Authorization"
    assert config_test.oriane_prefixe_auth == "Bearer "
    assert CLE_TEST not in repr(construire_config(Path("."), ORIANE_API_KEY=CLE_TEST))


def test_delai_d_expiration_lu_dans_la_configuration(tmp_path, transport_oriane_simule):
    config = construire_config(tmp_path, ORIANE_API_KEY=CLE_TEST, ORIANE_DELAI_S="7.5")
    base.configurer(config.chemin_base)
    transport = transport_oriane_simule()
    chercher(config, transport)
    assert transport.requetes[0].extensions["timeout"]["read"] == 7.5


@pytest.mark.parametrize("phrases", [[], [""], ["   "]])
def test_requete_sans_phrase_refusee(config_oriane, transport_oriane_simule, phrases):
    transport = transport_oriane_simule()
    with pytest.raises(RequeteInvalide):
        asyncio.run(rechercher(phrases, ["compte_simule_source"], config=config_oriane, transport=transport))
    assert transport.requetes == []


def test_fenetre_inversee_refusee(config_oriane, transport_oriane_simule):
    transport = transport_oriane_simule()
    inversee = Fenetre.model_construct(debut=FENETRE.fin, fin=FENETRE.debut)
    with pytest.raises(RequeteInvalide):
        chercher(config_oriane, transport, fenetre=inversee)
    assert transport.requetes == []


def test_cle_absente_ne_part_pas(config_test, transport_oriane_simule):
    transport = transport_oriane_simule()
    with pytest.raises(OrianeInjoignable, match="clé"):
        chercher(config_test, transport)
    assert transport.requetes == []


# --- succès, liste blanche -----------------------------------------------------------------------------


def test_reponse_projetee_vers_video_v1(config_oriane, transport_oriane_simule):
    resultat = chercher(config_oriane, transport_oriane_simule())
    assert resultat.code == 200
    assert resultat.total == 2
    assert resultat.ecartees == 0
    assert resultat.credits_estimes == 15
    assert not resultat.incomplete
    source, reprise = resultat.videos
    assert source.identifiant == "cnt_SIMULE0000000000000000000001"
    assert source.plateforme == "tiktok"
    assert source.compte == "compte_simule_source"
    assert source.identifiant_plateforme == "7000000000000000010"
    assert source.vues_selon_oriane == 12000
    assert source.interactions_selon_oriane == 800
    assert source.requetes_trouvees == [PHRASE]
    assert reprise.requetes_trouvees == [PHRASE]
    assert source.transcription.texte == "Propos simulé : il faut dix mille postes si l'État paie"
    assert source.transcription.source == "Oriane"
    assert source.transcription.niveau == "default"
    assert source.texte_ecran.texte == "TEXTE SIMULÉ : 10 000 postes"
    assert source.texte_ecran.source == "Oriane"
    assert source.lien == "https://www.tiktok.com/@compte_simule_source/video/7000000000000000010"
    assert source.mode == "direct"
    assert source.enregistre_le is None
    assert reprise.lien == "https://www.instagram.com/reel/CSIMULEREPRISE/"


def test_texte_a_l_ecran_en_liste_est_joint(config_oriane, transport_oriane_simule, reponse_oriane_simulee):
    reponse_oriane_simulee["data"]["results"][0]["media"][0]["onScreenText"] = [
        "PREMIÈRE LIGNE",
        "SECONDE LIGNE",
    ]
    resultat = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee))
    assert resultat.videos[0].texte_ecran.texte == "PREMIÈRE LIGNE\nSECONDE LIGNE"


def test_aucun_champ_de_tiers_dans_la_video_la_base_ni_le_journal(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    # La réponse simulée sert bien des champs de tiers : sinon le test ne prouverait rien.
    resultat0 = reponse_oriane_simulee["data"]["results"][0]
    presents = [n for n in CHAMPS_TIERS_ORIANE if n in resultat0]
    presents_media = [n for n in CHAMPS_TIERS_MEDIA_ORIANE if n in resultat0["media"][0]]
    assert len(presents) == len(CHAMPS_TIERS_ORIANE)
    assert len(presents_media) == len(CHAMPS_TIERS_MEDIA_ORIANE)
    tiers = valeurs_tiers(reponse_oriane_simulee)
    assert tiers

    resultat = chercher(config_oriane, transport_oriane_simule())
    produits = {
        "video": [v.model_dump(mode="json") for v in resultat.videos],
        "base": base.lister("video"),
        "journal": base.lire_journal(),
    }
    assert len(produits["base"]) == 2
    assert len(produits["journal"]) == 1
    for origine, contenu in produits.items():
        textes = feuilles(contenu)
        ensemble = "\n".join(textes)
        for nom in (*presents, *presents_media):
            assert nom not in textes, f"{nom} dans {origine}"
            assert f'"{nom}"' not in json.dumps(contenu), f"{nom} dans {origine}"
        for valeur in tiers:
            assert valeur not in ensemble, f"{valeur} dans {origine}"
    assert resultat.videos[0].model_dump().keys() == Video.model_fields.keys()


def test_champs_refuses_listes_dans_la_liste_blanche():
    assert set(CHAMPS_TIERS_ORIANE) - {"coAuthors"} <= liste_blanche.CHAMPS_REFUSES
    assert "coAuthors" in liste_blanche.CHAMPS_REFUSES
    assert set(CHAMPS_TIERS_MEDIA_ORIANE) == liste_blanche.CHAMPS_REFUSES_MEDIA
    assert not set(liste_blanche.CHAMPS_REFUSES) & set(liste_blanche.CORRESPONDANCE)


def test_resultat_incomplet_ecarte_sans_deviner(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    reponse_oriane_simulee["data"]["results"][1]["platform"] = "plateforme-inconnue"
    reponse_oriane_simulee["data"]["results"].append({"id": "cnt_SANS_COMPTE", "platform": "tiktok"})
    resultat = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee))
    assert len(resultat.videos) == 1
    assert resultat.ecartees == 2
    ligne = base.lire_journal()[0]
    assert ligne["resultats"] == {
        "retournes": 1,
        "ecartes": 2,
        "total_annonce": 2,
        "dits": 1,
        "ecrits": 0,
        "sans_origine": 0,
    }


def test_206_est_un_succes_incomplet(config_oriane, transport_oriane_simule, reponse_oriane_simulee):
    reponse_oriane_simulee["metadata"]["pagination"]["totalCount"] = 250
    resultat = chercher(config_oriane, transport_oriane_simule(statut=206, corps=reponse_oriane_simulee))
    assert resultat.code == 206
    assert resultat.total == 250
    assert resultat.incomplete
    assert len(resultat.videos) == 2
    assert base.lire_journal()[0]["code"] == 206


# --- erreurs -------------------------------------------------------------------------------------------


def test_401_authentification_refusee(config_oriane, transport_oriane_simule):
    corps = {"error": {"operation": "AUTHENTICATION", "code": "UNAUTHORIZED"}}
    with pytest.raises(OrianeInjoignable) as erreur:
        chercher(config_oriane, transport_oriane_simule(statut=401, corps=corps))
    assert erreur.value.raison == "authentification refusée"
    assert CLE_TEST not in str(erreur.value)
    assert base.lister("video") == []


def test_400_raison_avec_champ_et_message(config_oriane, transport_oriane_simule):
    corps = {
        "error": {
            "operation": "VALIDATION",
            "context": [{"field": "filters.platform", "rule": "type", "message": "doit être un objet"}],
        }
    }
    with pytest.raises(OrianeInjoignable) as erreur:
        chercher(config_oriane, transport_oriane_simule(statut=400, corps=corps))
    assert erreur.value.raison == "requête refusée : filters.platform doit être un objet"


def test_400_sans_contexte(config_oriane, transport_oriane_simule):
    with pytest.raises(OrianeInjoignable) as erreur:
        chercher(config_oriane, transport_oriane_simule(statut=400, corps={"error": {}}))
    assert erreur.value.raison == "requête refusée"


def test_402_credits_epuises(config_oriane, transport_oriane_simule):
    with pytest.raises(CreditsEpuises):
        chercher(config_oriane, transport_oriane_simule(statut=402, corps={"error": {"code": "PAYMENT"}}))


@pytest.mark.parametrize("statut", [403, 404, 429, 500, 503])
def test_autre_code_injoignable(config_oriane, transport_oriane_simule, statut):
    with pytest.raises(OrianeInjoignable, match=str(statut)):
        chercher(config_oriane, transport_oriane_simule(statut=statut, corps={"error": {}}))


def test_expiration_injoignable(config_oriane, transport_oriane_simule):
    transport = transport_oriane_simule(exception=httpx.ReadTimeout("trop lent"))
    with pytest.raises(OrianeInjoignable, match="expiration"):
        chercher(config_oriane, transport)
    ligne = base.lire_journal()[0]
    assert ligne["code"] is None
    assert ligne["resultats"] == {"erreur": "expiration"}


def test_coupure_reseau_injoignable(config_oriane, transport_oriane_simule):
    transport = transport_oriane_simule(exception=httpx.ConnectError("coupure"))
    with pytest.raises(OrianeInjoignable):
        chercher(config_oriane, transport)


@pytest.mark.parametrize("corps", [{"data": {}}, {"data": {"results": "x"}}, ["pas", "un", "objet"]])
def test_reponse_illisible(config_oriane, transport_oriane_simule, corps):
    with pytest.raises(OrianeInjoignable, match="illisible"):
        chercher(config_oriane, transport_oriane_simule(corps=corps))


# --- journal -------------------------------------------------------------------------------------------


def test_un_appel_une_ligne_de_journal(config_oriane, transport_oriane_simule):
    chercher(config_oriane, transport_oriane_simule(), comptes=["compte_simule_source"])
    (ligne,) = base.lire_journal()
    assert ligne["route"] == "oriane.recherche"
    assert ligne["cible"].startswith("POST /rest/contents/search?")
    assert ligne["code"] == 200
    assert ligne["mode"] == "direct"
    assert ligne["projection"] == "default"
    assert ligne["credits_estimes"] == 15
    assert ligne["duree_ms"] >= 0
    assert ligne["resultats"] == {
        "retournes": 2,
        "ecartes": 0,
        "total_annonce": 2,
        "dits": 2,
        "ecrits": 1,
        "sans_origine": 0,
    }
    # La requête envoyée est journalisée en clair, filtres compris.
    sous = ligne["filtres"]["queries"][0]["queries"]
    assert sous[0] == enfant("dit", "transcript", PHRASE)
    assert ligne["filtres"]["filters"]["profileHandle"] == {"exactMatch": ["compte_simule_source"]}


@pytest.mark.parametrize(
    ("statut", "exception"),
    [
        (200, None),
        (206, None),
        (401, None),
        (400, None),
        (402, None),
        (500, None),
        (200, httpx.ReadTimeout("x")),
    ],
)
def test_le_journal_ne_garde_ni_cle_ni_reponse_brute(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee, statut, exception
):
    transport = transport_oriane_simule(statut=statut, exception=exception)
    try:
        chercher(config_oriane, transport)
    except (OrianeInjoignable, CreditsEpuises):
        pass
    lignes = base.lire_journal()
    assert len(lignes) == 1
    texte = json.dumps(lignes, ensure_ascii=False)
    assert CLE_TEST not in texte
    assert "reponse" not in lignes[0]
    for valeur in valeurs_tiers(reponse_oriane_simulee) | {"Propos simulé", "req_SIMULE"}:
        assert valeur not in texte


# --- GET /v1/videos/{id} ----------------------------------------------------------------------------------


def valider_contre_schema(document: dict[str, Any], schema: dict[str, Any]) -> None:
    """Contrôle structurel contre `video.v1.schema.json` (pas de bibliothèque de schéma dans la pile)."""
    definitions = schema["$defs"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) <= set(document)
    assert set(document) <= set(schema["properties"])
    for nom, definition in (("transcription", "Transcription"), ("texte_ecran", "TexteEcran")):
        sous = definitions[definition]
        assert set(sous["required"]) <= set(document[nom]) <= set(sous["properties"])
        assert document[nom]["source"] == "Oriane"
    assert schema["properties"]["plateforme"]["enum"].count(document["plateforme"]) == 1


def test_route_sert_une_video_ecrite_en_base(config_oriane, transport_oriane_simule, client: TestClient):
    chercher(config_oriane, transport_oriane_simule())
    reponse = client.get("/v1/videos/cnt_SIMULE0000000000000000000001")
    assert reponse.status_code == 200
    document = reponse.json()
    schema = json.loads((RACINE_SERVICE / "contrats" / "video.v1.schema.json").read_text(encoding="utf-8"))
    valider_contre_schema(document, schema)
    video = Video.model_validate(document)
    assert video.transcription.source == "Oriane"
    assert video.transcription.niveau == "default"
    assert video.compte == "compte_simule_source"
    # Sans clé Oriane dans la configuration du service, la vidéo est servie comme enregistrée.
    assert document["mode"] == "enregistre"
    assert document["enregistre_le"] is not None
    textes = "\n".join(feuilles(document))
    assert not any(nom in textes for nom in (*CHAMPS_TIERS_ORIANE, *CHAMPS_TIERS_MEDIA_ORIANE))


def test_route_en_mode_direct(config_oriane, transport_oriane_simule):
    chercher(config_oriane, transport_oriane_simule())
    with TestClient(creer_application(config_oriane)) as client:
        document = client.get("/v1/videos/cnt_SIMULE0000000000000000000002").json()
    assert document["mode"] == "direct"
    assert document["enregistre_le"] is None


def test_route_mode_enregistre_force_jamais_direct(tmp_path, config_oriane, transport_oriane_simule):
    chercher(config_oriane, transport_oriane_simule())
    forcee = construire_config(tmp_path, ORIANE_API_KEY=CLE_TEST, MODE_DONNEES="enregistre")
    with TestClient(creer_application(forcee)) as client:
        document = client.get("/v1/videos/cnt_SIMULE0000000000000000000002").json()
    assert document["mode"] == "enregistre"
    assert document["enregistre_le"]


def test_route_video_inconnue_404_dans_l_enveloppe(client: TestClient):
    reponse = client.get("/v1/videos/absente")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"] == "introuvable"
    assert set(reponse.json()) == {"erreur", "detail", "mode"}


# --- appel réel (sauté sans clé) ---------------------------------------------------------------------------


@pytest.mark.reel
@pytest.mark.skipif(not os.environ.get("ORIANE_API_KEY"), reason="ORIANE_API_KEY absente")
def test_appel_reel_une_page_d_un_resultat(tmp_path):
    config = Configuration.depuis_environnement({**os.environ, "CHEMIN_BASE": str(tmp_path / "reel.sqlite")})
    base.configurer(config.chemin_base)
    base.initialiser()
    maintenant = datetime.now(UTC)
    fenetre = Fenetre(debut=maintenant - timedelta(days=7), fin=maintenant)
    resultat = asyncio.run(rechercher(["présidentielle"], config=config, fenetre=fenetre, limite=1))
    ligne = base.lire_journal()[0]
    print(  # noqa: T201 - compte rendu lisible avec `pytest -s`
        f"REEL code={resultat.code} total={resultat.total} ecartees={resultat.ecartees} "
        f"videos={len(resultat.videos)} duree_ms={ligne['duree_ms']}"
    )
    assert resultat.code in (200, 206)
    assert len(resultat.videos) <= 1
    for video in resultat.videos:
        assert video.transcription.source == "Oriane"
        assert video.transcription.niveau == "default"


# --- aperçu : vignette et images clés relayées -------------------------------------------------------


def test_apercu_rempli_depuis_la_vignette_et_les_images_cles(config_oriane, transport_oriane_simule):
    source, reprise = chercher(config_oriane, transport_oriane_simule()).videos
    assert source.apercu is not None
    assert source.apercu.vignette == "https://exemple.invalid/vignette-simulee.jpg"
    assert source.apercu.images_cles == ["https://exemple.invalid/image-simulee.jpg"]
    assert source.apercu.source == "Oriane"
    # Vignette seule : aucune image clé inventée.
    assert reprise.apercu is not None
    assert reprise.apercu.vignette == "https://exemple.invalid/vignette-simulee-2.jpg"
    assert reprise.apercu.images_cles == []


def test_apercu_absent_quand_oriane_ne_sert_rien(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    resultat0 = reponse_oriane_simulee["data"]["results"][0]
    del resultat0["thumbnailMediaUrl"]
    del resultat0["media"][0]["frames"]
    video = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee)).videos[0]
    assert video.apercu is None
    assert "apercu" not in video.model_dump(mode="json", exclude_none=True)


def test_apercu_dix_images_cles_au_plus_et_aucune_adresse_deduite(
    config_oriane, transport_oriane_simule, reponse_oriane_simulee
):
    resultat0 = reponse_oriane_simulee["data"]["results"][0]
    resultat0["media"][0]["frames"] = [
        {"url": f"https://exemple.invalid/image-{i}.jpg"} for i in range(15)
    ] + [
        {"url": "http://exemple.invalid/non-https.jpg"},
        {"id": "sans-adresse"},
        "pas-un-objet",
    ]
    resultat0["thumbnailMediaUrl"] = "pas-une-adresse"
    video = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee)).videos[0]
    assert video.apercu is not None
    assert video.apercu.vignette is None
    assert video.apercu.images_cles == [f"https://exemple.invalid/image-{i}.jpg" for i in range(10)]


def test_apercu_dedoublonne_les_images_cles(config_oriane, transport_oriane_simule, reponse_oriane_simulee):
    resultat0 = reponse_oriane_simulee["data"]["results"][0]
    resultat0["media"][0]["frames"] = [
        {"url": "https://exemple.invalid/a.jpg"},
        {"url": "https://exemple.invalid/b.jpg"},
        {"url": "https://exemple.invalid/a.jpg"},
    ]
    video = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee)).videos[0]
    assert video.apercu is not None
    assert video.apercu.images_cles == ["https://exemple.invalid/a.jpg", "https://exemple.invalid/b.jpg"]


def test_apercu_images_cles_sans_vignette(config_oriane, transport_oriane_simule, reponse_oriane_simulee):
    resultat0 = reponse_oriane_simulee["data"]["results"][0]
    del resultat0["thumbnailMediaUrl"]
    video = chercher(config_oriane, transport_oriane_simule(corps=reponse_oriane_simulee)).videos[0]
    assert video.apercu is not None
    assert video.apercu.vignette is None
    assert video.apercu.images_cles == ["https://exemple.invalid/image-simulee.jpg"]


def test_apercu_ne_porte_aucun_nom_oriane():
    schema = json.dumps(Video.model_json_schema())
    for nom in ("thumbnailMediaUrl", "frames", "thumbnailMediaId"):
        assert nom not in schema
    assert "thumbnailMediaId" in liste_blanche.CHAMPS_REFUSES
    assert "thumbnailMediaUrl" in liste_blanche.CORRESPONDANCE
