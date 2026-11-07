"""Socle du service (S01) : configuration, santé, CORS, enveloppe d'erreur, clé de démonstration, base."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import base
from app.config import Configuration, ErreurConfiguration
from app.erreurs import ErreurApi
from app.main import creer_application
from tests.conftest import CLE_DEMO_TEST, ORIGINE_LOVABLE

ENVELOPPE = {"erreur", "detail", "mode"}


class Corps(BaseModel):
    """Corps de la requête POST d'essai."""

    nom: str


def ajouter_routes_essai(client: TestClient) -> None:
    """Déclare des routes d'essai sous /v1 (le routeur du socle est vide)."""

    @client.app.get("/v1/essai")
    async def lire_essai() -> dict[str, bool]:
        return {"ok": True}

    @client.app.post("/v1/essai")
    async def ecrire_essai(corps: Corps) -> dict[str, str]:
        return {"nom": corps.nom}


# --- configuration -----------------------------------------------------------------------------


def test_config_sans_cle_est_enregistre_avec_raison():
    config = Configuration.depuis_environnement({})
    assert config.mode == "enregistre"
    assert "ORIANE_API_KEY" in config.raison


def test_config_avec_cle_est_direct():
    config = Configuration.depuis_environnement({"ORIANE_API_KEY": "cle-factice"})
    assert config.mode == "direct"
    assert "cle-factice" not in repr(config)


def test_config_mode_donnees_enregistre_force_le_mode():
    config = Configuration.depuis_environnement(
        {"ORIANE_API_KEY": "cle-factice", "MODE_DONNEES": "enregistre"}
    )
    assert config.mode == "enregistre"
    assert "MODE_DONNEES" in config.raison


def test_config_valeurs_par_defaut():
    config = Configuration.depuis_environnement({})
    assert config.oriane_delai_s == 20
    assert config.plafond_credits_jour == 600
    assert config.port == 8080
    assert config.cle_demo == ""


def test_config_origines_vides_n_autorise_aucune_origine():
    assert Configuration.depuis_environnement({}).origines_autorisees == ()
    assert Configuration.depuis_environnement({"ORIGINES_AUTORISEES": " , "}).origines_autorisees == ()


def test_config_origines_separees_par_des_virgules():
    config = Configuration.depuis_environnement({"ORIGINES_AUTORISEES": "https://a.test, https://b.test/"})
    assert config.origines_autorisees == ("https://a.test", "https://b.test")


def test_config_refuse_l_origine_etoile():
    with pytest.raises(ErreurConfiguration):
        Configuration.depuis_environnement({"ORIGINES_AUTORISEES": "*"})


def test_config_refuse_un_mode_donnees_inconnu():
    with pytest.raises(ErreurConfiguration):
        Configuration.depuis_environnement({"MODE_DONNEES": "direct"})


# --- santé --------------------------------------------------------------------------------------


def test_sante(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"etat": "ok", "version": "0.1.0", "mode": "enregistre", "enregistre_le": None}


# --- CORS ---------------------------------------------------------------------------------------


def test_cors_origine_autorisee(client):
    reponse = client.get("/sante", headers={"Origin": ORIGINE_LOVABLE})
    assert reponse.headers["access-control-allow-origin"] == ORIGINE_LOVABLE


def test_cors_origine_non_autorisee(client):
    reponse = client.get("/sante", headers={"Origin": "https://autre.exemple"})
    assert "access-control-allow-origin" not in reponse.headers


def test_cors_sans_origine_declaree_refuse_toute_origine(tmp_path):
    config = Configuration.depuis_environnement({"CHEMIN_BASE": str(tmp_path / "b.sqlite")})
    with TestClient(creer_application(config)) as c:
        reponse = c.get("/sante", headers={"Origin": ORIGINE_LOVABLE})
    assert "access-control-allow-origin" not in reponse.headers


def test_cors_pre_verification_liste_la_cle_demo(client):
    reponse = client.options(
        "/v1/essai",
        headers={
            "Origin": ORIGINE_LOVABLE,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Cle-Demo, Content-Type",
        },
    )
    assert reponse.status_code == 200
    assert reponse.headers["access-control-allow-origin"] == ORIGINE_LOVABLE
    autorises = reponse.headers["access-control-allow-headers"].lower()
    assert "x-cle-demo" in autorises
    assert "content-type" in autorises


# --- clé de démonstration -----------------------------------------------------------------------


def test_cle_demo_vide_avertit_au_journal(client):
    entrees = [e for e in base.lire_journal() if e["route"] == "demarrage"]
    assert len(entrees) == 1
    assert "CLE_DEMO vide" in entrees[0]["cible"]


def test_cle_demo_vide_journalise_aussi_un_avertissement(config_test, caplog):
    with caplog.at_level(logging.WARNING, logger="tete_de_brut"):
        with TestClient(creer_application(config_test)):
            pass
    assert any("CLE_DEMO vide" in message for message in caplog.messages)


def test_service_ouvert_sans_cle_demo(client):
    ajouter_routes_essai(client)
    assert client.post("/v1/essai", json={"nom": "a"}).status_code == 200


def test_cle_demo_post_sans_en_tete_rend_401_dans_l_enveloppe(client_avec_cle):
    ajouter_routes_essai(client_avec_cle)
    reponse = client_avec_cle.post("/v1/essai", json={"nom": "a"})
    assert reponse.status_code == 401
    assert set(reponse.json()) == ENVELOPPE
    assert reponse.json()["erreur"] == "cle_demo_invalide"
    assert reponse.json()["mode"] == "enregistre"


def test_cle_demo_mauvaise_valeur_rend_401(client_avec_cle):
    ajouter_routes_essai(client_avec_cle)
    reponse = client_avec_cle.post("/v1/essai", json={"nom": "a"}, headers={"X-Cle-Demo": "mauvaise"})
    assert reponse.status_code == 401


def test_cle_demo_bonne_valeur_laisse_passer(client_avec_cle):
    ajouter_routes_essai(client_avec_cle)
    reponse = client_avec_cle.post("/v1/essai", json={"nom": "a"}, headers={"X-Cle-Demo": CLE_DEMO_TEST})
    assert reponse.status_code == 200
    assert reponse.json() == {"nom": "a"}


def test_cle_demo_ne_ferme_ni_get_ni_sante(client_avec_cle):
    ajouter_routes_essai(client_avec_cle)
    assert client_avec_cle.get("/v1/essai").status_code == 200
    assert client_avec_cle.get("/sante").status_code == 200


def test_cle_demo_reponse_401_porte_les_en_tetes_cors(client_avec_cle):
    reponse = client_avec_cle.post("/v1/essai", json={}, headers={"Origin": ORIGINE_LOVABLE})
    assert reponse.status_code == 401
    assert reponse.headers["access-control-allow-origin"] == ORIGINE_LOVABLE


# --- enveloppe d'erreur -------------------------------------------------------------------------


def test_404_dans_l_enveloppe(client):
    reponse = client.get("/v1/n-existe-pas")
    assert reponse.status_code == 404
    assert set(reponse.json()) == ENVELOPPE
    assert reponse.json()["erreur"] == "introuvable"


def test_405_dans_l_enveloppe(client):
    reponse = client.post("/sante")
    assert reponse.status_code == 405
    assert set(reponse.json()) == ENVELOPPE
    assert reponse.json()["erreur"] == "methode_non_permise"


def test_422_dans_l_enveloppe(client):
    ajouter_routes_essai(client)
    reponse = client.post("/v1/essai", json={"autre": 1})
    assert reponse.status_code == 422
    assert set(reponse.json()) == ENVELOPPE
    assert reponse.json()["erreur"] == "validation"
    assert "nom" in reponse.json()["detail"]


def test_erreur_api_dans_l_enveloppe(client):
    @client.app.get("/v1/conflit")
    async def conflit():
        raise ErreurApi("decision_manquante", "Aucune décision enregistrée.", 409)

    reponse = client.get("/v1/conflit")
    assert reponse.status_code == 409
    assert reponse.json() == {
        "erreur": "decision_manquante",
        "detail": "Aucune décision enregistrée.",
        "mode": "enregistre",
    }


# --- base SQLite et journal ---------------------------------------------------------------------


@pytest.fixture
def base_temporaire(tmp_path: Path):
    """Pointe le module `base` sur un fichier temporaire, puis restaure le chemin précédent."""
    precedent = base._chemin_courant
    base.configurer(tmp_path / "essai.sqlite")
    yield tmp_path / "essai.sqlite"
    base.configurer(precedent)


def test_base_ecrire_lire_lister(base_temporaire):
    base.ecrire("video", "v1", "video.v1", {"identifiant": "v1", "texte": "é"})
    base.ecrire("video", "v2", "video.v1", {"identifiant": "v2"})
    assert base.lire("video", "v1") == {"identifiant": "v1", "texte": "é"}
    assert base.lire("video", "absent") is None
    assert base.lire("recit", "v1") is None
    assert [o["identifiant"] for o in base.lister("video")] == ["v1", "v2"]
    assert base.lister("recit") == []


def test_base_ecrire_remplace_le_meme_identifiant(base_temporaire):
    base.ecrire("fiche", "f1", "fiche.v1", {"etat": "brouillon"})
    base.ecrire("fiche", "f1", "fiche.v1", {"etat": "tranchee"})
    assert base.lire("fiche", "f1") == {"etat": "tranchee"}
    assert len(base.lister("fiche")) == 1


def test_base_cree_le_dossier(tmp_path):
    chemin = tmp_path / "sous" / "dossier" / "b.sqlite"
    base.ecrire("video", "v1", "video.v1", {}, chemin=chemin)
    assert chemin.exists()


def test_journal_consigner_et_lire(base_temporaire):
    identifiant = base.consigner(
        route="/v1/radar/actualiser",
        cible="oriane",
        filtres={"requete": "retraites", "limite": 100},
        projection=["id", "compte"],
        resultats=12,
        credits_estimes=15,
        duree_ms=420.5,
        code=200,
        mode="direct",
    )
    assert identifiant == 1
    base.consigner(route="/v1/videos/v1", code=200, mode="enregistre")
    journal = base.lire_journal()
    assert [e["route"] for e in journal] == ["/v1/videos/v1", "/v1/radar/actualiser"]
    premier = journal[1]
    assert premier["filtres"] == {"requete": "retraites", "limite": 100}
    assert premier["projection"] == ["id", "compte"]
    assert premier["resultats"] == 12
    assert premier["credits_estimes"] == 15
    assert premier["heure"]
    assert len(base.lire_journal(limite=1)) == 1


def test_journal_refuse_le_champ_reponse(base_temporaire):
    with pytest.raises(base.ErreurJournal):
        base.consigner(route="/v1/radar", reponse={"data": [1, 2, 3]})
    assert base.lire_journal() == []


def test_journal_refuse_un_champ_inconnu(base_temporaire):
    with pytest.raises(base.ErreurJournal):
        base.consigner(route="/v1/radar", corps="x")


def test_journal_refuse_une_valeur_contenant_une_cle(base_temporaire, monkeypatch):
    with pytest.raises(base.ErreurJournal):
        base.consigner(route="/v1/radar", filtres={"api_key": "abc"})
    with pytest.raises(base.ErreurJournal):
        base.consigner(route="/v1/radar", cible="Bearer abcdef")
    monkeypatch.setenv("ORIANE_API_KEY", "valeur-factice-123")
    with pytest.raises(base.ErreurJournal):
        base.consigner(route="/v1/radar", cible="appel avec valeur-factice-123")
    assert base.lire_journal() == []
