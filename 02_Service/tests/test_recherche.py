"""Recherche à la demande (S13) : traduction, RG-02, préparation sans appel, exécution, mode enregistré.

Aucun réseau : Oriane est jouée par `httpx.MockTransport` (`tests/conftest.py`), le cas est simulé.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import recherche as module_recherche
from app.config import Configuration
from app.libelles import contient_libelle_refuse
from app.liste_blanche import CHAMPS_REFUSES
from app.main import creer_application
from app.modeles import Recherche, ResultatRecherche
from app.oriane import construire_corps
from app.recherche import DETAIL_NOM_SEUL, MESSAGE_HORS_CAS, preparer
from tests.conftest import CAS_ENREGISTRE_LE, CAS_PHRASE, construire_config

CLE_ORIANE_TEST = "cle-fictive-pour-les-tests-0001"
MAINTENANT = datetime(2026, 11, 7, 14, 30, 12, tzinfo=UTC)
COMPTES_PARTIS = ["compte_parti_simule_1", "compte_parti_simule_2", "compte_parti_simule_3"]
AUTRE_PHRASE = "autre phrase simulée"
ID_TIKTOK = "7000000000000000010"
LIEN_TIKTOK = f"https://www.tiktok.com/@compte_simule_source/video/{ID_TIKTOK}"
NOMS_ORIANE = ("platformId", "publishedAt", "onScreenText", "transcript", "profileHandle", "viewsCount")
QUESTION_DU_MANDAT = "Que dit-on depuis hier sur « places de crèche en 2027 », hors comptes de partis ?"


def _ecrire_comptes(tmp_path: Path) -> Path:
    chemin = tmp_path / "comptes.json"
    chemin.write_text(
        json.dumps({"partis": ["@" + COMPTES_PARTIS[0], *COMPTES_PARTIS[1:]]}), encoding="utf-8"
    )
    return chemin


@pytest.fixture
def config_traduction(tmp_path: Path) -> Configuration:
    """Configuration de test avec la liste de comptes de partis (fictifs)."""
    return construire_config(tmp_path, CHEMIN_COMPTES=str(_ecrire_comptes(tmp_path)))


@contextmanager
def _service(
    tmp_path: Path,
    *,
    direct: bool,
    transport: httpx.MockTransport | None = None,
    **env: str,
) -> Iterator[TestClient]:
    environnement = {"CHEMIN_COMPTES": str(_ecrire_comptes(tmp_path)), **env}
    if direct:
        environnement["ORIANE_API_KEY"] = CLE_ORIANE_TEST
    config = construire_config(tmp_path, **environnement)
    with TestClient(creer_application(config)) as client:
        if transport is not None:
            client.app.state.transport_oriane = transport
        yield client


@pytest.fixture
def direct(
    tmp_path: Path, transport_oriane_simule: Callable[..., httpx.MockTransport]
) -> Iterator[tuple[TestClient, httpx.MockTransport]]:
    """Service en direct : clé fictive, Oriane simulée ; `transport.requetes` garde les appels."""
    transport = transport_oriane_simule()
    with _service(tmp_path, direct=True, transport=transport) as client:
        yield client, transport


def _preparer(client: TestClient, question: str) -> Any:
    reponse = client.post("/v1/recherches/preparer", json={"question": question})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def _lancer(client: TestClient, question: str) -> Any:
    return client.post("/v1/recherches", json={"question": question})


def _corps_envoye(transport: httpx.MockTransport) -> dict[str, Any]:
    assert len(transport.requetes) == 1  # type: ignore[attr-defined]
    return json.loads(transport.requetes[0].content)  # type: ignore[attr-defined]


def _appels_oriane(client: TestClient) -> list[dict[str, Any]]:
    entrees = client.get("/v1/journal").json()["entrees"]
    return [e for e in entrees if e["route"] == "oriane.recherche"]


# --- traduction : six questions types, déterministe -------------------------------------------------


@pytest.mark.parametrize(
    ("question", "phrase", "debut", "plateformes", "exclus"),
    [
        # 1. la question du mandat : guillemets, « depuis hier », exclusion des partis
        (QUESTION_DU_MANDAT, "places de crèche en 2027", "2026-11-06", [], COMPTES_PARTIS),
        # 2. sans guillemets, sans consigne : la question est la phrase, fenêtre de 7 jours par défaut
        ("places de crèche en 2027", "places de crèche en 2027", "2026-10-31", [], []),
        # 3. amorce, « depuis N jours », deux plateformes
        (
            "Que dit-on sur dix mille postes depuis 3 jours sur tiktok et instagram ?",
            "dix mille postes",
            "2026-11-04",
            ["tiktok", "instagram"],
            [],
        ),
        # 4. guillemets droits, « 48 h », une plateforme
        ('"dix mille postes" 48 h sur youtube', "dix mille postes", "2026-11-05", ["youtube"], []),
        # 5. « 24 h » et « 7 jours » en toutes lettres
        ("« la réforme passe » dans les dernières 24 heures", "la réforme passe", "2026-11-06", [], []),
        ("la réforme passe sur les 7 derniers jours", "la réforme passe", "2026-10-31", [], []),
        # 6. un mot de la phrase qui ressemble à une consigne reste dans la phrase entre guillemets
        ("« 24 h chrono sur tiktok » depuis 2 jours", "24 h chrono sur tiktok", "2026-11-05", [], []),
    ],
)
def test_traduction_des_questions_types(
    config_traduction: Configuration,
    question: str,
    phrase: str,
    debut: str,
    plateformes: list[str],
    exclus: list[str],
) -> None:
    recherche = preparer(question, config_traduction, maintenant=MAINTENANT)
    assert recherche.type == "phrase" and recherche.refus is None
    filtres = recherche.filtres
    assert filtres.phrases == [phrase]
    assert filtres.dans == "parole ou texte à l'écran"
    assert filtres.fenetre is not None
    assert filtres.fenetre.debut.isoformat() == f"{debut}T00:00:00+00:00"
    assert filtres.fenetre.fin == MAINTENANT.replace(microsecond=0)
    assert filtres.plateformes == plateformes
    assert filtres.comptes_exclus == exclus
    assert filtres.comptes == [] and filtres.identifiant_plateforme is None
    assert recherche.cout_estime.credits_estimes == 15
    assert f"« {phrase} »" in recherche.requete_en_clair
    assert recherche.question == question


def test_traduction_deterministe(config_traduction: Configuration) -> None:
    premiere = preparer(QUESTION_DU_MANDAT, config_traduction, maintenant=MAINTENANT)
    seconde = preparer(QUESTION_DU_MANDAT, config_traduction, maintenant=MAINTENANT)
    # `enregistre_le` suit l'horloge quand aucun cas n'est enregistré : seul le reste est comparé.
    assert premiere.model_dump(exclude={"enregistre_le"}) == seconde.model_dump(exclude={"enregistre_le"})


@pytest.mark.parametrize(
    ("lien", "plateforme", "identifiant"),
    [
        (LIEN_TIKTOK + "?lang=fr", "tiktok", ID_TIKTOK),
        ("www.tiktok.com/@compte_simule/video/7000000000000000011", "tiktok", "7000000000000000011"),
        ("https://www.instagram.com/reel/CSIMULEREPRISE/", "instagram", "CSIMULEREPRISE"),
        ("https://instagram.com/compte_simule/p/CSIMULEPOST_1-/", "instagram", "CSIMULEPOST_1-"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3s", "youtube", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/AbCdEfGhIjK", "youtube", "AbCdEfGhIjK"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube", "dQw4w9WgXcQ"),
        ("regarde ça : https://youtu.be/dQw4w9WgXcQ.", "youtube", "dQw4w9WgXcQ"),
    ],
)
def test_un_lien_devient_une_recherche_par_identifiant(
    config_traduction: Configuration, lien: str, plateforme: str, identifiant: str
) -> None:
    recherche = preparer(lien, config_traduction, maintenant=MAINTENANT)
    assert recherche.type == "lien" and recherche.refus is None
    filtres = recherche.filtres
    assert filtres.plateformes == [plateforme]
    assert filtres.identifiant_plateforme == identifiant
    assert filtres.phrases == [] and filtres.dans is None and filtres.fenetre is None
    assert recherche.cout_estime.credits_estimes == 15
    assert identifiant in recherche.requete_en_clair


@pytest.mark.parametrize(
    "lien",
    [
        "https://vm.tiktok.com/ZMabcdefg/",
        "https://www.tiktok.com/@compte_simule",
        "https://www.instagram.com/compte_simule/",
        "https://www.youtube.com/@chaine_simulee",
    ],
)
def test_un_lien_sans_identifiant_de_video_est_refuse(config_traduction: Configuration, lien: str) -> None:
    recherche = preparer(lien, config_traduction, maintenant=MAINTENANT)
    assert recherche.type == "lien"
    assert recherche.refus is not None and recherche.refus.code == "lien_non_reconnu"
    assert recherche.cout_estime.credits_estimes == 0


def test_un_nom_de_domaine_voisin_n_est_pas_un_lien(config_traduction: Configuration) -> None:
    recherche = preparer("monyoutube.com/watch?v=dQw4w9WgXcQ", config_traduction, maintenant=MAINTENANT)
    assert recherche.type == "phrase"


def test_exclusion_sans_liste_configuree_est_dite_pas_ignoree(config_test: Configuration) -> None:
    recherche = preparer(QUESTION_DU_MANDAT, config_test, maintenant=MAINTENANT)
    assert recherche.refus is None and recherche.filtres.comptes_exclus == []
    assert "exclusion « comptes de partis » non appliquée" in recherche.requete_en_clair
    assert "aucune liste de comptes « partis » n'est configurée" in recherche.requete_en_clair


@pytest.mark.parametrize(
    ("contenu", "raison"),
    [
        (None, "introuvable"),
        ("{pas du json", "illisible"),
        (json.dumps({"partis": "pas une liste"}), "mal formée"),
    ],
)
def test_liste_de_comptes_inutilisable_est_dite(tmp_path: Path, contenu: str | None, raison: str) -> None:
    chemin = tmp_path / "comptes.json"
    if contenu is not None:
        chemin.write_text(contenu, encoding="utf-8")
    config = construire_config(tmp_path, CHEMIN_COMPTES=str(chemin))
    recherche = preparer(QUESTION_DU_MANDAT, config, maintenant=MAINTENANT)
    assert recherche.filtres.comptes_exclus == []
    assert raison in recherche.requete_en_clair


def test_le_mot_sans_n_est_pas_une_exclusion(config_traduction: Configuration) -> None:
    recherche = preparer("régularisation des sans papiers", config_traduction, maintenant=MAINTENANT)
    assert recherche.filtres.phrases == ["régularisation des sans papiers"]
    assert recherche.filtres.comptes_exclus == []


# --- RG-02 et autres refus ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question", ["Jean Dupont", "Marie", "« Jean Dupont »", "Marie-Claire Dupont", "Émilie"]
)
def test_rg02_refuse_le_seul_nom_d_une_personne(config_traduction: Configuration, question: str) -> None:
    recherche = preparer(question, config_traduction, maintenant=MAINTENANT)
    assert recherche.refus is not None
    assert recherche.refus.code == "nom_seul"
    assert recherche.refus.detail == DETAIL_NOM_SEUL
    assert recherche.cout_estime.credits_estimes == 0
    assert recherche.requete_en_clair == "recherche refusée : rien n'est envoyé à Oriane"


@pytest.mark.parametrize(
    "question",
    ["places de crèche en 2027", "Dupont annonce 300 places", "Jean Dupont 2027", "la réforme des retraites"],
)
def test_rg02_accepte_une_phrase(config_traduction: Configuration, question: str) -> None:
    assert preparer(question, config_traduction, maintenant=MAINTENANT).refus is None


@pytest.mark.parametrize(
    ("question", "code"),
    [
        ("« premier » « second »", "plusieurs_phrases"),
        ("depuis hier sur tiktok", "aucune_phrase"),
        ("« »", "aucune_phrase"),
        ("« " + "mot " * 80 + "»", "phrase_trop_longue"),
    ],
)
def test_autres_refus_sans_appel(config_traduction: Configuration, question: str, code: str) -> None:
    recherche = preparer(question, config_traduction, maintenant=MAINTENANT)
    assert recherche.refus is not None and recherche.refus.code == code
    assert recherche.cout_estime.credits_estimes == 0


def test_textes_du_service_sans_libelle_refuse(config_traduction: Configuration) -> None:
    for texte in (DETAIL_NOM_SEUL, MESSAGE_HORS_CAS, module_recherche._DETAIL_LIEN):
        assert contient_libelle_refuse(texte) is None, texte
    for question in (QUESTION_DU_MANDAT, "Jean Dupont", LIEN_TIKTOK, "« a » « b »", "depuis hier"):
        recherche = preparer(question, config_traduction, maintenant=MAINTENANT)
        textes = [recherche.requete_en_clair, recherche.cout_estime.methode]
        if recherche.refus:
            textes.append(recherche.refus.detail)
        for texte in textes:
            assert contient_libelle_refuse(texte) is None, texte


# --- les routes : validation, préparation sans appel ---------------------------------------------------


@pytest.mark.parametrize("chemin", ["/v1/recherches/preparer", "/v1/recherches"])
@pytest.mark.parametrize("corps", [{"question": ""}, {"question": "   "}, {}, {"question": 12}, {"q": "x"}])
def test_question_vide_ou_absente_rend_422(client: TestClient, chemin: str, corps: dict[str, Any]) -> None:
    reponse = client.post(chemin, json=corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"] == "validation"
    assert reponse.json()["mode"] == "enregistre"


def test_preparer_n_appelle_pas_oriane(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, transport = direct
    corps = _preparer(client, QUESTION_DU_MANDAT)
    _preparer(client, LIEN_TIKTOK)
    _preparer(client, "Jean Dupont")
    assert transport.requetes == []  # type: ignore[attr-defined]
    assert _appels_oriane(client) == []
    assert corps["mode"] == "direct" and corps["enregistre_le"] is None
    assert corps["type"] == "phrase" and corps["refus"] is None
    assert corps["cout_estime"]["credits_estimes"] == 15
    assert "15 crédits par page" in corps["cout_estime"]["methode"]
    assert corps["filtres"]["comptes_exclus"] == COMPTES_PARTIS
    assert Recherche.model_validate(corps).filtres.phrases == ["places de crèche en 2027"]
    # rien n'est écrit : le radar reste vide
    assert client.get("/v1/radar").json()["recits"] == []


def test_preparer_refus_rg02_rend_200_avec_le_libelle(client: TestClient) -> None:
    corps = _preparer(client, "Jean Dupont")
    assert corps["refus"] == {"code": "nom_seul", "detail": DETAIL_NOM_SEUL}
    assert corps["cout_estime"]["credits_estimes"] == 0
    assert corps["mode"] == "enregistre" and corps["enregistre_le"]


# --- exécution en direct ---------------------------------------------------------------------------------


def test_filtres_affiches_sont_ceux_envoyes(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, transport = direct
    question = f"Que dit-on depuis hier sur « {CAS_PHRASE} » sur tiktok, hors comptes de partis ?"
    prepare = _preparer(client, question)
    reponse = _lancer(client, question)
    assert reponse.status_code == 201, reponse.text
    affiche = reponse.json()["recherche"]["filtres"]
    assert affiche["phrases"] == prepare["filtres"]["phrases"] == [CAS_PHRASE]
    assert affiche["comptes_exclus"] == prepare["filtres"]["comptes_exclus"] == COMPTES_PARTIS
    assert affiche["plateformes"] == prepare["filtres"]["plateformes"] == ["tiktok"]
    assert affiche["fenetre"]["debut"] == prepare["filtres"]["fenetre"]["debut"]

    envoye = _corps_envoye(transport)
    filtres = envoye["filters"]
    jour = lambda iso: iso[:10]  # noqa: E731
    assert filtres["publishedAt"] == {
        "after": jour(affiche["fenetre"]["debut"]),
        "before": jour(affiche["fenetre"]["fin"]),
    }
    assert filtres["platform"] == {"includes": ["tiktok"]}
    assert filtres["profileHandle"] == {"excludesExactly": {"values": COMPTES_PARTIS, "operator": "or"}}
    enfants = envoye["queries"][0]["queries"]
    envoyees = {e["filters"][fil]["includesExactly"]["values"][0] for e in enfants for fil in e["filters"]}
    assert envoyees == {CAS_PHRASE}
    assert {fil for e in enfants for fil in e["filters"]} == {"transcript", "onScreenText"}


def test_recherche_ajoute_le_recit_au_radar(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, _ = direct
    avant = client.get("/v1/radar").json()
    assert avant["recits"] == []
    reponse = _lancer(client, f"« {CAS_PHRASE} »")
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["mode"] == "direct" and corps["enregistre_le"] is None
    assert corps["video"] is None
    recit = corps["recit"]
    assert recit["phrase_surveillee"] == CAS_PHRASE and recit["mode"] == "direct"
    assert len(recit["videos"]) == 2
    assert {m["nom"] for m in recit["mesures"]}  # chaque mesure garde méthode et fenêtre (règle S05)
    assert all(m["methode"] and m["fenetre"] for m in recit["mesures"])
    ResultatRecherche.model_validate(corps)

    radar = client.get("/v1/radar").json()
    assert [r["identifiant"] for r in radar["recits"]] == [recit["identifiant"]]
    assert radar["calcule_le"] >= avant["calcule_le"]
    assert client.get(f"/v1/recits/{recit['identifiant']}").status_code == 200
    for identifiant in recit["videos"]:
        assert client.get(f"/v1/videos/{identifiant}").status_code == 200


def test_cout_estime_egal_cout_journalise(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, _ = direct
    estime = _preparer(client, f"« {CAS_PHRASE} »")["cout_estime"]["credits_estimes"]
    reponse = _lancer(client, f"« {CAS_PHRASE} »")
    assert reponse.json()["recherche"]["cout_estime"]["credits_estimes"] == estime
    appels = _appels_oriane(client)
    assert len(appels) == 1  # une entrée par appel Oriane
    assert appels[0]["credits_estimes"] == estime == 15
    assert client.get("/v1/etat").json()["credits_du_jour"] == estime


def test_lien_rend_la_video_trouvee_par_son_identifiant(
    direct: tuple[TestClient, httpx.MockTransport],
) -> None:
    client, transport = direct
    reponse = _lancer(client, LIEN_TIKTOK)
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["recit"] is None
    assert corps["recherche"]["type"] == "lien"
    assert corps["video"]["identifiant_plateforme"] == ID_TIKTOK
    assert corps["video"]["plateforme"] == "tiktok" and corps["video"]["mode"] == "direct"
    envoye = _corps_envoye(transport)
    assert envoye["filters"]["platformId"] == {"includes": [{"platform": "tiktok", "platformId": ID_TIKTOK}]}
    assert "queries" not in envoye and "publishedAt" not in envoye["filters"]
    assert client.get(f"/v1/videos/{corps['video']['identifiant']}").status_code == 200
    assert client.get("/v1/radar").json()["recits"] == []  # un lien n'ajoute aucun récit
    assert (
        _appels_oriane(client)[0]["credits_estimes"] == corps["recherche"]["cout_estime"]["credits_estimes"]
    )


def test_lien_que_oriane_ne_retrouve_pas_rend_404(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, _ = direct
    reponse = _lancer(client, "https://www.tiktok.com/@compte_simule/video/7999999999999999999")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"] == "introuvable" and reponse.json()["mode"] == "direct"


def test_refus_rg02_rend_422_sans_aucun_appel(direct: tuple[TestClient, httpx.MockTransport]) -> None:
    client, transport = direct
    for question in ("Jean Dupont", "Marie"):
        reponse = _lancer(client, question)
        assert reponse.status_code == 422
        assert reponse.json() == {"erreur": "validation", "detail": DETAIL_NOM_SEUL, "mode": "direct"}
    assert transport.requetes == []  # type: ignore[attr-defined]
    assert _appels_oriane(client) == []


def test_une_seconde_recherche_garde_les_videos_de_la_premiere(
    direct: tuple[TestClient, httpx.MockTransport],
    reponse_oriane_simulee: dict[str, Any],
    transport_oriane_simule: Callable[..., httpx.MockTransport],
) -> None:
    client, _ = direct
    assert _lancer(client, f"« {CAS_PHRASE} »").status_code == 201
    for resultat in reponse_oriane_simulee["data"]["results"]:
        resultat["matchedQueries"] = [f"dit:{AUTRE_PHRASE}"]
    client.app.state.transport_oriane = transport_oriane_simule(corps=reponse_oriane_simulee)
    assert _lancer(client, f"« {AUTRE_PHRASE} »").status_code == 201
    recits = {r["phrase_surveillee"]: r for r in client.get("/v1/radar").json()["recits"]}
    assert set(recits) == {CAS_PHRASE, AUTRE_PHRASE}
    assert len(recits[CAS_PHRASE]["videos"]) == 2
    assert len(recits[AUTRE_PHRASE]["videos"]) == 2


@pytest.mark.parametrize(
    ("statut", "exception", "erreur"),
    [(401, None, "oriane_injoignable"), (None, httpx.ReadTimeout("expiré"), "oriane_injoignable")],
)
def test_panne_d_oriane_rend_503_dans_l_enveloppe(
    tmp_path: Path,
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    statut: int | None,
    exception: Exception | None,
    erreur: str,
) -> None:
    transport = transport_oriane_simule(statut=statut or 200, exception=exception)
    with _service(tmp_path, direct=True, transport=transport) as client:
        reponse = _lancer(client, f"« {CAS_PHRASE} »")
        assert reponse.status_code == 503
        assert reponse.json()["erreur"] == erreur and reponse.json()["mode"] == "direct"


# --- bascule en mode enregistré --------------------------------------------------------------------------


def test_credits_epuises_bascule_et_sert_le_cas(
    tmp_path: Path,
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    cas_simule: Callable[..., Path],
) -> None:
    transport = transport_oriane_simule(statut=402, corps={})
    with _service(tmp_path, direct=True, transport=transport) as client:
        cas_simule(client.app.state.config)
        reponse = _lancer(client, f"« {CAS_PHRASE} »")
        assert reponse.status_code == 201
        assert reponse.json()["mode"] == "enregistre" and reponse.json()["recit"]["videos"]
        assert client.get("/v1/etat").json()["mode"] == "enregistre"
        hors_cas = _lancer(client, f"« {AUTRE_PHRASE} »")
        assert hors_cas.status_code == 409 and hors_cas.json()["mode"] == "enregistre"


def test_deux_pannes_de_suite_bascule_au_second_appel(
    tmp_path: Path,
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    cas_simule: Callable[..., Path],
) -> None:
    transport = transport_oriane_simule(exception=httpx.ReadTimeout("expiré"))
    with _service(tmp_path, direct=True, transport=transport) as client:
        cas_simule(client.app.state.config)
        assert _lancer(client, f"« {CAS_PHRASE} »").status_code == 503
        seconde = _lancer(client, f"« {CAS_PHRASE} »")
        assert seconde.status_code == 201 and seconde.json()["mode"] == "enregistre"


def test_plafond_de_credits_bascule_avant_tout_appel(
    tmp_path: Path,
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    cas_simule: Callable[..., Path],
) -> None:
    transport = transport_oriane_simule()
    with _service(tmp_path, direct=True, transport=transport, PLAFOND_CREDITS_JOUR="10") as client:
        cas_simule(client.app.state.config)
        reponse = _lancer(client, f"« {CAS_PHRASE} »")
        assert reponse.status_code == 201 and reponse.json()["mode"] == "enregistre"
        assert transport.requetes == []  # type: ignore[attr-defined]


# --- mode enregistré ---------------------------------------------------------------------------------------


@pytest.fixture
def enregistre(tmp_path: Path, cas_simule: Callable[..., Path]) -> Iterator[TestClient]:
    """Service sans clé Oriane (mode enregistré) sur le cas simulé."""
    with _service(tmp_path, direct=False) as client:
        cas_simule(client.app.state.config)
        yield client


def test_enregistre_prepare_dit_le_mode_et_la_date(enregistre: TestClient) -> None:
    corps = _preparer(enregistre, f"« {CAS_PHRASE} »")
    assert corps["mode"] == "enregistre"
    assert datetime.fromisoformat(corps["enregistre_le"]) == CAS_ENREGISTRE_LE
    assert corps["cout_estime"]["credits_estimes"] == 15
    assert "0 crédit dépensé" in corps["cout_estime"]["methode"]
    assert corps["refus"] is None


def test_enregistre_sert_une_phrase_du_cas_sans_appel(enregistre: TestClient) -> None:
    # La casse et la ponctuation ne comptent pas : même normalisation `mots.v1` que les récits.
    reponse = _lancer(enregistre, "« Dix mille, postes ! »")
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["mode"] == "enregistre"
    assert datetime.fromisoformat(corps["enregistre_le"]) == CAS_ENREGISTRE_LE
    assert corps["recherche"]["mode"] == corps["recit"]["mode"] == "enregistre"
    assert len(corps["recit"]["videos"]) == 2 and corps["video"] is None
    assert corps["recit"]["enregistre_le"]
    ResultatRecherche.model_validate(corps)
    assert [
        e for e in enregistre.get("/v1/journal").json()["entrees"] if e["route"] == "oriane.recherche"
    ] == []
    assert enregistre.get("/v1/radar").json()["recits"][0]["identifiant"] == corps["recit"]["identifiant"]


def test_enregistre_refuse_une_phrase_hors_du_cas(enregistre: TestClient) -> None:
    reponse = _lancer(enregistre, f"« {AUTRE_PHRASE} »")
    assert reponse.status_code == 409
    assert reponse.json() == {
        "erreur": "recherche_indisponible",
        "detail": "Mode enregistré : seules les phrases du cas sont servies",
        "mode": "enregistre",
    }


def test_enregistre_sert_un_lien_du_cas_et_refuse_les_autres(enregistre: TestClient) -> None:
    identifiant = ID_TIKTOK  # vidéo 1 du cas simulé (compte_simule_1)
    reponse = _lancer(enregistre, f"https://www.tiktok.com/@compte_simule_1/video/{identifiant}")
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["recit"] is None and corps["video"]["identifiant_plateforme"] == identifiant
    assert corps["video"]["mode"] == "enregistre" and corps["mode"] == "enregistre"
    inconnu = _lancer(enregistre, "https://www.tiktok.com/@compte_simule_1/video/7999999999999999999")
    assert inconnu.status_code == 404 and inconnu.json()["erreur"] == "introuvable"
    assert inconnu.json()["mode"] == "enregistre"


def test_enregistre_sans_cas_aucune_recherche_n_est_servie(client: TestClient) -> None:
    assert _lancer(client, f"« {CAS_PHRASE} »").status_code == 409
    assert _lancer(client, LIEN_TIKTOK).status_code == 404


# --- contrat : aucun nom Oriane ---------------------------------------------------------------------------


def _cles(objet: Any) -> set[str]:
    if isinstance(objet, dict):
        return set(objet) | {c for v in objet.values() for c in _cles(v)}
    if isinstance(objet, list):
        return {c for v in objet for c in _cles(v)}
    return set()


def test_aucun_nom_de_champ_oriane_dans_les_reponses(
    direct: tuple[TestClient, httpx.MockTransport],
) -> None:
    client, _ = direct
    reponses = [
        _preparer(client, QUESTION_DU_MANDAT),
        _preparer(client, LIEN_TIKTOK),
        _preparer(client, "Jean Dupont"),
        _lancer(client, f"« {CAS_PHRASE} »").json(),
        _lancer(client, LIEN_TIKTOK).json(),
    ]
    interdits = set(NOMS_ORIANE) | CHAMPS_REFUSES | {"includesExactly", "excludesExactly", "exactMatch"}
    for corps in reponses:
        assert not _cles(corps) & interdits


# --- construction du corps d'Oriane ------------------------------------------------------------------------


def test_corps_oriane_comptes_exclus_et_identifiants() -> None:
    corps = construire_corps(
        [CAS_PHRASE], comptes_exclus=["a", " b "], identifiants_plateforme=[("tiktok", ID_TIKTOK)]
    )
    assert corps["filters"]["profileHandle"] == {"excludesExactly": {"values": ["a", "b"], "operator": "or"}}
    assert corps["filters"]["platformId"] == {"includes": [{"platform": "tiktok", "platformId": ID_TIKTOK}]}
    assert len(corps["queries"][0]["queries"]) == 2
    sans_phrase = construire_corps([], identifiants_plateforme=[("tiktok", ID_TIKTOK)])
    assert "queries" not in sans_phrase and sans_phrase["operator"] == "and"


def test_corps_oriane_sans_phrase_ni_identifiant_reste_refuse() -> None:
    from app.oriane import RequeteInvalide

    with pytest.raises(RequeteInvalide):
        construire_corps([])


# --- phrases cherchées et radar (F016b) -----------------------------------------------------------------


def _reponse_pour(reponse_oriane: dict[str, Any], phrase: str) -> dict[str, Any]:
    """La réponse simulée, dont les deux vidéos sont trouvées par `phrase`."""
    for resultat in reponse_oriane["data"]["results"]:
        resultat["matchedQueries"] = [f"dit:{phrase}"]
    return reponse_oriane


def test_une_phrase_cherchee_apparait_au_radar_du_cas(
    tmp_path: Path,
    reponse_oriane_simulee: dict[str, Any],
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    cas_simule: Callable[..., Path],
) -> None:
    # Avec un cas chargé par l'actualisation, le radar ne lit que les documents de phrases surveillées :
    # sans le document écrit par la recherche, la phrase cherchée n'y serait pas.
    with _service(tmp_path, direct=True, transport=transport_oriane_simule()) as client:
        cas_simule(client.app.state.config)
        assert client.post("/v1/radar/actualiser").status_code == 200
        client.app.state.transport_oriane = transport_oriane_simule(
            corps=_reponse_pour(reponse_oriane_simulee, AUTRE_PHRASE)
        )
        assert _lancer(client, f"« {AUTRE_PHRASE} »").status_code == 201
        recits = {r["phrase_surveillee"]: r for r in client.get("/v1/radar").json()["recits"]}
        assert set(recits) == {CAS_PHRASE, AUTRE_PHRASE}
        assert len(recits[AUTRE_PHRASE]["videos"]) == 2


def test_apres_la_bascule_le_radar_n_a_pas_de_recit_vide(
    tmp_path: Path,
    reponse_oriane_simulee: dict[str, Any],
    transport_oriane_simule: Callable[..., httpx.MockTransport],
    cas_simule: Callable[..., Path],
) -> None:
    with _service(tmp_path, direct=True, transport=transport_oriane_simule()) as client:
        cas_simule(client.app.state.config)
        assert client.post("/v1/radar/actualiser").status_code == 200
        client.app.state.transport_oriane = transport_oriane_simule(
            corps=_reponse_pour(reponse_oriane_simulee, AUTRE_PHRASE)
        )
        assert _lancer(client, f"« {AUTRE_PHRASE} »").status_code == 201
        assert len(client.get("/v1/radar").json()["recits"]) == 2
        # Un 402 bascule en mode enregistré : les vidéos lues en direct sont purgées du radar.
        client.app.state.transport_oriane = transport_oriane_simule(statut=402, corps={})
        assert _lancer(client, "« encore une autre phrase simulée »").status_code == 409
        radar = client.get("/v1/radar").json()
        assert radar["mode"] == "enregistre"
        assert [r["phrase_surveillee"] for r in radar["recits"]] == [CAS_PHRASE]
        assert all(r["videos"] for r in radar["recits"])
