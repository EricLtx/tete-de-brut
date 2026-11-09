"""Modes direct et enregistré (S04) : bascule, plafond, état, journal, cas enregistré, script.

Aucun réseau ni clé réelle : `httpx.MockTransport` joue Oriane, le cas est simulé.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import acquisition, base, cas
from app.main import creer_application
from app.oriane import ResultatRecherche
from tests.conftest import (
    CAS_ENREGISTRE_LE,
    CAS_PHRASE,
    CLE_DEMO_TEST,
    ORIGINE_LOVABLE,
    construire_config,
    fabriquer_video,
)

CLE_TEST = "cle-fictive-pour-les-tests-0001"
RACINE_SERVICE = Path(__file__).resolve().parent.parent
ID_VIDEO = "cnt_SIMULE0000000000000000000001"
DATE_DU_CAS = CAS_ENREGISTRE_LE.isoformat().replace("+00:00", "Z")


@pytest.fixture
def service(tmp_path, cas_simule, transport_oriane_simule) -> Iterator[Callable[..., TestClient]]:
    """Ouvre un service avec clé fictive et cas simulé : `service(transport=None, ecrire_cas=True, **env)`."""
    ouverts: list[TestClient] = []

    def ouvrir(transport: httpx.MockTransport | None = None, ecrire_cas: bool = True, **env: str):
        config = construire_config(tmp_path, ORIANE_API_KEY=CLE_TEST, **env)
        if ecrire_cas:
            cas_simule(config)
        c = TestClient(creer_application(config))
        c.__enter__()
        c.app.state.transport_oriane = transport or transport_oriane_simule()
        ouverts.append(c)
        return c

    yield ouvrir
    for c in ouverts:
        c.__exit__(None, None, None)


def en_expiration() -> httpx.MockTransport:
    def repondre(requete: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("expiré")

    return httpx.MockTransport(repondre)


def sans_appel() -> httpx.MockTransport:
    def repondre(requete: httpx.Request) -> httpx.Response:
        pytest.fail("aucun appel à Oriane n'était attendu")

    return httpx.MockTransport(repondre)


# --- état -----------------------------------------------------------------------------------------


def test_etat_sans_cle_est_enregistre_avec_son_cas(client, config_test, cas_simule):
    cas_simule(config_test)
    etat = client.get("/v1/etat").json()
    assert etat["mode"] == "enregistre"
    assert "ORIANE_API_KEY absente" in etat["raison"]
    assert etat["enregistre_le"] == DATE_DU_CAS
    assert (etat["credits_du_jour"], etat["plafond_credits_jour"]) == (0, 600)
    assert etat["contrat"] == "api.v1"
    assert etat["version"]


def test_etat_sans_cas_le_dit(client):
    etat = client.get("/v1/etat").json()
    assert etat["mode"] == "enregistre"
    assert etat["enregistre_le"] is None
    assert "aucun cas enregistré" in etat["raison"]


def test_apres_l_etat_le_radar_porte_les_recits_du_cas(client, config_test, cas_simule):
    cas_simule(config_test)
    client.get("/v1/etat")
    radar = client.get("/v1/radar").json()
    assert radar["mode"] == "enregistre"
    assert [r["phrase_surveillee"] for r in radar["recits"]] == [CAS_PHRASE]
    assert len(radar["recits"][0]["videos"]) == 2


def test_mode_enregistre_force_meme_avec_cle(service):
    c = service(transport=sans_appel(), MODE_DONNEES="enregistre")
    etat = c.get("/v1/etat").json()
    assert etat["mode"] == "enregistre"
    assert "MODE_DONNEES=enregistre" in etat["raison"]
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 200
    assert reponse.json()["mode"] == "enregistre"
    assert reponse.json()["cout_actualisation"]["credits_estimes"] == 0


def test_cas_avec_champ_de_tiers_est_refuse_au_chargement(client, config_test, cas_simule):
    chemin = cas_simule(config_test)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    document["videos"][0]["popularComments"] = [{"text": "commentaire simulé"}]
    chemin.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(cas.CasInvalide, match="popularComments"):
        cas.lire_cas(config_test)
    etat = client.get("/v1/etat").json()
    assert etat["enregistre_le"] is None
    assert "refusé" in etat["raison"]


def test_cas_avec_image_ou_champ_inconnu_est_refuse(config_test, cas_simule):
    chemin = cas_simule(config_test)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    document["videos"][0]["legende"] = "https://exemple.invalid/image-simulee.jpg"
    with pytest.raises(cas.CasInvalide, match="image"):
        cas.valider(document)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    document["biographie"] = "x"
    with pytest.raises(cas.CasInvalide, match="hors liste blanche"):
        cas.valider(document)


def test_cas_avec_apercu_https_est_accepte(config_test, cas_simule):
    chemin = cas_simule(config_test)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    document["videos"][0]["apercu"] = {
        "vignette": "https://exemple.invalid/vignette.jpg",
        "images_cles": ["https://exemple.invalid/image.jpg"],
        "source": "Oriane",
        "lue_le": "2026-11-07T09:00:00+00:00",
    }
    enregistre = cas.valider(document)
    assert enregistre.videos[0].apercu is not None
    assert enregistre.videos[0].apercu.images_cles == ["https://exemple.invalid/image.jpg"]


@pytest.mark.parametrize(
    "adresse", ["http://exemple.invalid/p.gif", "javascript:alert(1)", "data:text/plain,x", "texte libre"]
)
@pytest.mark.parametrize("champ", ["vignette", "images_cles"])
def test_cas_avec_apercu_non_https_est_refuse(config_test, cas_simule, champ, adresse):
    chemin = cas_simule(config_test)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    apercu = {"vignette": None, "images_cles": [], "source": "Oriane", "lue_le": "2026-11-07T09:00:00+00:00"}
    apercu[champ] = adresse if champ == "vignette" else ["https://exemple.invalid/ok.jpg", adresse]
    document["videos"][0]["apercu"] = apercu
    with pytest.raises(cas.CasInvalide):
        cas.valider(document)


def test_fichier_du_cas_en_mode_direct_est_rejoue_en_enregistre(config_test, cas_simule):
    chemin = cas_simule(config_test)
    document = json.loads(chemin.read_text(encoding="utf-8"))
    for video in document["videos"]:
        video["mode"] = "direct"
        video["enregistre_le"] = None
    assert {v.mode for v in cas.valider(document).videos} == {"enregistre"}


# --- bascules ---------------------------------------------------------------------------------------


def test_deux_expirations_basculent_en_enregistre(service):
    c = service(transport=en_expiration())
    premiere = c.post("/v1/radar/actualiser")
    assert premiere.status_code == 503
    assert premiere.json()["erreur"] == "oriane_injoignable"
    assert c.get("/v1/etat").json()["mode"] == "direct"
    seconde = c.post("/v1/radar/actualiser")
    assert seconde.status_code == 200
    radar = seconde.json()
    assert radar["mode"] == "enregistre"
    assert radar["raison"].startswith("Oriane injoignable")
    assert radar["enregistre_le"] == DATE_DU_CAS
    etat = c.get("/v1/etat").json()
    assert (etat["mode"], etat["raison"]) == ("enregistre", radar["raison"])
    assert c.get("/v1/radar").json()["mode"] == "enregistre"


def test_une_expiration_puis_un_succes_ne_bascule_pas(service, transport_oriane_simule):
    c = service(transport=en_expiration())
    assert c.post("/v1/radar/actualiser").status_code == 503
    c.app.state.transport_oriane = transport_oriane_simule()
    assert c.post("/v1/radar/actualiser").json()["mode"] == "direct"
    c.app.state.transport_oriane = en_expiration()
    assert c.post("/v1/radar/actualiser").status_code == 503  # le compteur est reparti de zéro
    assert c.get("/v1/etat").json()["mode"] == "direct"


def test_plafond_atteint_aucun_appel_ne_part(service):
    c = service(transport=sans_appel(), PLAFOND_CREDITS_JOUR="10")
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 200
    radar = reponse.json()
    assert radar["mode"] == "enregistre"
    assert "plafond" in radar["raison"]
    etat = c.get("/v1/etat").json()
    assert (etat["mode"], etat["plafond_credits_jour"]) == ("enregistre", 10)


def test_402_bascule_et_dit_pourquoi(service, transport_oriane_simule):
    c = service(
        transport=transport_oriane_simule(statut=402, corps={"error": {"message": "plus de crédits"}})
    )
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 200
    assert reponse.json()["mode"] == "enregistre"
    assert "402" in reponse.json()["raison"]


def test_401_oriane_ne_bascule_pas(service, transport_oriane_simule):
    c = service(transport=transport_oriane_simule(statut=401, corps={}))
    for _ in range(3):
        reponse = c.post("/v1/radar/actualiser")
        assert reponse.status_code == 503
        assert "authentification" in reponse.json()["detail"]
    assert c.get("/v1/etat").json()["mode"] == "direct"


def test_succes_en_direct_chiffre_le_cout_et_les_credits_du_jour(service):
    c = service()
    radar = c.post("/v1/radar/actualiser").json()
    assert radar["mode"] == "direct"
    assert radar["enregistre_le"] is None
    assert radar["cout_actualisation"]["credits_estimes"] == 15
    assert [r["phrase_surveillee"] for r in radar["recits"]] == [CAS_PHRASE]
    etat = c.get("/v1/etat").json()
    assert (etat["mode"], etat["credits_du_jour"], etat["enregistre_le"]) == ("direct", 15, None)
    assert c.get(f"/v1/videos/{ID_VIDEO}").json()["mode"] == "direct"


def test_un_resultat_enregistre_n_est_jamais_servi_en_direct(service, transport_oriane_simule):
    c = service()
    assert c.post("/v1/radar/actualiser").json()["mode"] == "direct"
    assert c.get(f"/v1/videos/{ID_VIDEO}").json()["mode"] == "direct"
    c.app.state.transport_oriane = transport_oriane_simule(statut=402, corps={})
    assert c.post("/v1/radar/actualiser").json()["mode"] == "enregistre"
    video = c.get(f"/v1/videos/{ID_VIDEO}").json()
    assert video["mode"] == "enregistre"
    assert video["enregistre_le"] is not None
    assert all(r["mode"] == "enregistre" for r in c.get("/v1/radar").json()["recits"])


# --- clé de démonstration, RG-02, journal --------------------------------------------------------------


def test_actualiser_sans_cle_de_demo_est_refuse(service):
    c = service(transport=sans_appel(), CLE_DEMO=CLE_DEMO_TEST)
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 401
    assert reponse.json()["erreur"] == "cle_demo_invalide"


def test_phrase_de_moins_de_trois_mots_refusee_avec_raison():
    assert cas.verifier_phrases(["dix mille postes"]) is None
    for phrase in ("Dupont", "Jean Dupont", ""):
        assert "RG-02" in (cas.verifier_phrases(["dix mille postes", phrase]) or "")
    assert cas.verifier_phrases([]) == "aucune phrase à surveiller"


def test_actualiser_refuse_une_phrase_trop_courte_avant_tout_appel(service):
    c = service(transport=sans_appel(), ecrire_cas=False)
    chemin = cas.fichier_cas(c.app.state.config)
    chemin.parent.mkdir(parents=True)
    document = {"enregistre_le": CAS_ENREGISTRE_LE.isoformat(), "phrases": ["Jean Dupont"], "videos": []}
    chemin.write_text(json.dumps(document), encoding="utf-8")
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 422
    assert "RG-02" in reponse.json()["detail"]
    assert c.get("/v1/etat").json()["mode"] == "direct"


def test_actualiser_sans_cas_refuse(service):
    c = service(transport=sans_appel(), ecrire_cas=False)
    reponse = c.post("/v1/radar/actualiser")
    assert reponse.status_code == 422
    assert reponse.json()["erreur"] == "validation"


def test_journal_sert_les_appels_et_les_bascules_sans_cle(service, transport_oriane_simule):
    c = service()
    c.post("/v1/radar/actualiser")
    c.app.state.transport_oriane = transport_oriane_simule(statut=402, corps={})
    c.post("/v1/radar/actualiser")
    reponse = c.get("/v1/journal", params={"limite": 10})
    assert reponse.status_code == 200
    journal = reponse.json()
    assert journal["mode"] == "enregistre"
    assert journal["enregistre_le"]
    routes = [e["route"] for e in journal["entrees"]]
    assert routes[0] == "acquisition.bascule"  # le plus récent d'abord
    assert "oriane.recherche" in routes
    assert CLE_TEST not in reponse.text
    assert c.get("/v1/journal", params={"limite": 0}).status_code == 422


# --- script d'enregistrement ----------------------------------------------------------------------------


def charger_script() -> Any:
    spec = importlib.util.spec_from_file_location(
        "enregistrer_cas", RACINE_SERVICE / "scripts/enregistrer_cas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ecrire_requetes(tmp_path: Path, phrases: list[str] | None = None) -> Path:
    chemin = tmp_path / "requetes.json"
    chemin.write_text(json.dumps({"phrases": phrases or [CAS_PHRASE]}), encoding="utf-8")
    return chemin


def test_script_ecrit_un_cas_sans_champ_de_tiers(tmp_path, transport_oriane_simule):
    script = charger_script()
    config = construire_config(tmp_path, ORIANE_API_KEY=CLE_TEST)
    sortie = tmp_path / "sortie" / "cas.json"
    chemin, ecrit = asyncio.run(
        script.enregistrer(config, {"phrases": [CAS_PHRASE]}, sortie, transport=transport_oriane_simule())
    )
    assert chemin == sortie
    texte = sortie.read_text(encoding="utf-8")
    document = json.loads(texte)
    assert cas.champs_refuses(document) == []
    assert len(document["videos"]) == len(ecrit.videos) == 2
    assert {v["mode"] for v in document["videos"]} == {"enregistre"}
    assert document["credits_estimes"] == 15
    assert CLE_TEST not in texte
    assert cas.valider(document).phrases == [CAS_PHRASE]


def test_script_refuse_un_cas_contenant_popular_comments(tmp_path, monkeypatch, capsys):
    script = charger_script()
    monkeypatch.setenv("ORIANE_API_KEY", CLE_TEST)
    monkeypatch.setenv("CHEMIN_BASE", str(tmp_path / "base.sqlite"))
    sortie = tmp_path / "cas.json"

    async def faux_rechercher(phrases, comptes, fenetre, **options):
        return ResultatRecherche(
            videos=[fabriquer_video()], total=1, ecartees=0, code=200, credits_estimes=15, requete={}
        )

    original = cas.construire_document

    def avec_commentaires(**champs):
        document = original(**champs)
        document["videos"][0]["popularComments"] = [{"text": "commentaire simulé d'un tiers"}]
        return document

    monkeypatch.setattr(script, "rechercher", faux_rechercher)
    monkeypatch.setattr(cas, "construire_document", avec_commentaires)
    arguments = [str(ecrire_requetes(tmp_path)), "--sortie", str(sortie), "--env", str(tmp_path / "x.env")]
    assert script.main(arguments) == 1
    assert "popularComments" in capsys.readouterr().err
    assert not sortie.exists()


def test_script_refuse_une_phrase_de_moins_de_trois_mots(tmp_path, monkeypatch, capsys):
    script = charger_script()
    monkeypatch.setenv("ORIANE_API_KEY", CLE_TEST)
    sortie = tmp_path / "cas.json"
    requetes = ecrire_requetes(tmp_path, ["Jean Dupont"])
    arguments = [str(requetes), "--sortie", str(sortie), "--env", str(tmp_path / "x.env")]
    assert script.main(arguments) == 1
    assert "RG-02" in capsys.readouterr().err
    assert not sortie.exists()


def test_script_sans_cle_refuse_et_n_accepte_pas_la_cle_en_argument(tmp_path, monkeypatch, capsys):
    script = charger_script()
    monkeypatch.delenv("ORIANE_API_KEY", raising=False)
    requetes = ecrire_requetes(tmp_path)
    assert script.main([str(requetes), "--env", str(tmp_path / "x.env")]) == 1
    assert "ORIANE_API_KEY absente" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        script.main([str(requetes), "--cle", "x"])


def test_script_lit_la_cle_dans_le_env(tmp_path, monkeypatch):
    script = charger_script()
    monkeypatch.delenv("ORIANE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text('# commentaire\nORIANE_API_KEY="cle-fictive-env"\n', encoding="utf-8")
    script.charger_env(env)
    assert os.environ["ORIANE_API_KEY"] == "cle-fictive-env"
    monkeypatch.delenv("ORIANE_API_KEY")


def test_radar_en_premier_apres_demarrage_porte_les_recits(client_avec_cas):
    radar = client_avec_cas.get("/v1/radar").json()
    assert radar["mode"] == "enregistre"
    assert [r["phrase_surveillee"] for r in radar["recits"]] == [CAS_PHRASE]
    assert len(radar["recits"][0]["videos"]) == 2


@pytest.fixture
def client_avec_cas(config_test, cas_simule) -> Iterator[TestClient]:
    cas_simule(config_test)
    with TestClient(creer_application(config_test)) as c:
        yield c


def test_radar_enregistre_ne_compte_que_les_videos_du_cas(
    service, reponse_oriane_simulee, transport_oriane_simule
):
    c = service()
    for i, resultat in enumerate(reponse_oriane_simulee["data"]["results"]):
        resultat["id"] = f"cnt_DIRECT00000000000000000000{i}"
        resultat["platformId"] = f"71000000000000000{i}"
    en_direct = transport_oriane_simule(corps=reponse_oriane_simulee)
    c.app.state.transport_oriane = en_direct
    radar = c.post("/v1/radar/actualiser").json()
    assert radar["mode"] == "direct"
    assert len(radar["recits"][0]["videos"]) == 2
    c.app.state.transport_oriane = transport_oriane_simule(statut=402, corps={})
    enregistre = c.post("/v1/radar/actualiser").json()
    assert enregistre["mode"] == "enregistre"
    videos = enregistre["recits"][0]["videos"]
    assert sorted(videos) == [ID_VIDEO, ID_VIDEO.replace("1", "2")]
    assert c.get("/v1/videos/cnt_DIRECT000000000000000000000").status_code == 404


def test_rejeu_laisse_une_ligne_au_journal_et_sante_donne_la_date(service):
    c = service(MODE_DONNEES="enregistre")
    assert c.get("/sante").json()["enregistre_le"] == DATE_DU_CAS.replace("Z", "+00:00")
    c.post("/v1/radar/actualiser")
    assert c.get("/v1/journal").json()["entrees"][0]["route"] == "acquisition.rejeu"


# --- plafond sous appels simultanés, purge ciblée, sortie du script de parcours (F023, S20) ----------------


def test_trois_actualisations_simultanees_sous_un_plafond_de_20_une_seule_appelle_oriane(
    service, reponse_oriane_simulee
):
    requetes: list[httpx.Request] = []

    async def repondre(requete: httpx.Request) -> httpx.Response:
        requete.read()
        requetes.append(requete)
        await asyncio.sleep(0.05)  # des appels non gardés se chevaucheraient ici
        return httpx.Response(200, json=reponse_oriane_simulee)

    c = service(transport=httpx.MockTransport(repondre), PLAFOND_CREDITS_JOUR="20")

    async def trois():
        return await asyncio.gather(*(acquisition.actualiser(c.app) for _ in range(3)))

    radars = asyncio.run(trois())
    assert len(requetes) == 1
    assert sorted(r.mode for r in radars) == ["direct", "enregistre", "enregistre"]
    assert acquisition.credits_du_jour() == 15
    assert "plafond" in c.get("/v1/etat").json()["raison"]


def test_la_bascule_ne_purge_que_les_documents_de_recherche(service, transport_oriane_simule):
    c = service()
    assert c.post("/v1/radar/actualiser").json()["mode"] == "direct"
    base.ecrire("cas", "recherche-x", "cas.v1", {"phrases": ["phrase d'une recherche"]})
    base.ecrire("cas", "cas-futur", "cas.v1", {"phrases": ["phrase d'un autre émetteur"]})
    c.app.state.transport_oriane = transport_oriane_simule(statut=402, corps={})
    assert c.post("/v1/radar/actualiser").json()["mode"] == "enregistre"
    identifiants = sorted(i for i, _ in base.lister_avec_identifiants("cas"))
    assert identifiants == ["cas-futur", cas.IDENTIFIANT_CAS]


def test_le_script_de_parcours_n_imprime_aucun_compte(client_avec_cas, capsys):
    spec = importlib.util.spec_from_file_location(
        "verifier_parcours", RACINE_SERVICE / "scripts/verifier_parcours.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    parcours = script.Parcours(client_avec_cas, ORIGINE_LOVABLE, "")
    sortie = []
    for nom, geste in script.GESTES:
        sortie.append(f"OK  {nom} : {geste(parcours)}")  # un geste en échec lèverait `Echec`
    texte = " ".join(sortie) + capsys.readouterr().out
    assert "compte_simule" not in texte
    assert ID_VIDEO in texte  # les vidéos restent nommées par leur identifiant
