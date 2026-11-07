"""Radar des récits (S05) : regroupement par phrase, mesures, plus ancienne version, routes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import base
from app.libelles import contient_libelle_refuse
from app.mesures import mesures_de_volume
from app.modeles import LIBELLE_PLUS_ANCIENNE_VERSION, Fenetre, Mesure, Recit
from tests.conftest import fabriquer_video

PHRASE_A = "dix mille postes"
PHRASE_B = "la réforme passe"


def _poser(*videos) -> None:
    for v in videos:
        base.ecrire("video", v.identifiant, "video.v1", v.model_dump(mode="json"))


def _trois_videos():
    return (
        fabriquer_video(
            identifiant="v-a-recente",
            compte="compte_simule_a",
            publie_le="2026-11-06T10:00:00+00:00",
            vues_selon_oriane=1000,
            requetes_trouvees=[PHRASE_A],
        ),
        fabriquer_video(
            identifiant="v-a-ancienne",
            compte="compte_simule_b",
            publie_le="2026-11-03T10:00:00+00:00",
            vues_selon_oriane=500,
            requetes_trouvees=[PHRASE_A],
        ),
        fabriquer_video(
            identifiant="v-b",
            compte="compte_simule_a",
            publie_le="2026-11-04T10:00:00+00:00",
            vues_selon_oriane=250,
            requetes_trouvees=[PHRASE_B],
        ),
    )


def _mesure(recit: dict, nom: str) -> dict:
    return next(m for m in recit["mesures"] if m["nom"] == nom)


def _valider_recit(donnees: dict) -> None:
    """Valide contre `contrats/recit.v1.schema.json` (champs requis et connus) et contre le modèle."""
    schema = json.loads(
        (Path(__file__).parent.parent / "contrats" / "recit.v1.schema.json").read_text("utf-8")
    )
    assert set(schema["required"]) <= set(donnees)
    assert set(donnees) <= set(schema["properties"])
    Recit.model_validate(donnees)


def test_base_vide_radar_vide(client: TestClient) -> None:
    reponse = client.get("/v1/radar")
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["recits"] == []
    assert donnees["mode"] == "enregistre"
    assert donnees["enregistre_le"]
    assert donnees["calcule_le"]


def test_base_vide_non_cherche_renseigne_sur_un_cas(client: TestClient) -> None:
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A]})
    recit = client.get("/v1/radar").json()["recits"][0]
    assert recit["videos"] == []
    assert recit["plus_ancienne_version"] is None
    assert _mesure(recit, "videos_trouvees")["valeur"] == 0
    vues = _mesure(recit, "vues_cumulees")
    assert vues["valeur"] is None and vues["raison"]
    assert len(recit["non_cherche"]) >= 4
    _valider_recit(recit)


def test_trois_videos_deux_phrases(client: TestClient) -> None:
    _poser(*_trois_videos())
    donnees = client.get("/v1/radar").json()
    assert len(donnees["recits"]) == 2
    par_phrase = {r["phrase_surveillee"]: r for r in donnees["recits"]}
    a, b = par_phrase[PHRASE_A], par_phrase[PHRASE_B]
    assert _mesure(a, "videos_trouvees")["valeur"] == 2
    assert _mesure(a, "comptes_distincts")["valeur"] == 2
    assert _mesure(a, "vues_cumulees")["valeur"] == 1500
    assert _mesure(b, "videos_trouvees")["valeur"] == 1
    assert _mesure(b, "comptes_distincts")["valeur"] == 1
    assert _mesure(b, "vues_cumulees")["valeur"] == 250
    assert a["plus_ancienne_version"]["video"] == "v-a-ancienne"
    assert a["plus_ancienne_version"]["libelle"] == LIBELLE_PLUS_ANCIENNE_VERSION
    assert a["videos"] == ["v-a-ancienne", "v-a-recente"]
    for recit in donnees["recits"]:
        _valider_recit(recit)
        for mesure in recit["mesures"]:
            assert mesure["methode"] and mesure["fenetre"]["debut"] and mesure["fenetre"]["fin"]
            assert mesure["echantillon"]["limite_page"] == 100


def test_phrases_du_cas_prioritaires_et_identifiant_stable(client: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A], "requete": "requête de cas lisible"})
    donnees = client.get("/v1/radar").json()
    assert [r["phrase_surveillee"] for r in donnees["recits"]] == [PHRASE_A]
    assert donnees["recits"][0]["requete_en_clair"] == "requête de cas lisible"
    de_nouveau = client.get("/v1/radar").json()
    assert de_nouveau["recits"][0]["identifiant"] == donnees["recits"][0]["identifiant"]


def test_une_video_deux_phrases_compte_dans_les_deux_recits(client: TestClient) -> None:
    _poser(fabriquer_video(identifiant="v-double", requetes_trouvees=[PHRASE_A, PHRASE_B]))
    recits = client.get("/v1/radar").json()["recits"]
    assert [r["videos"] for r in recits] == [["v-double"], ["v-double"]]


def test_recit_par_identifiant_puis_introuvable(client: TestClient) -> None:
    _poser(*_trois_videos())
    recit = client.get("/v1/radar").json()["recits"][0]
    reponse = client.get(f"/v1/recits/{recit['identifiant']}")
    assert reponse.status_code == 200
    assert reponse.json()["identifiant"] == recit["identifiant"]
    _valider_recit(reponse.json())
    absent = client.get("/v1/recits/recit-inconnu")
    assert absent.status_code == 404
    assert absent.json()["erreur"] == "introuvable"


def test_page_pleine_marquee_tronquee() -> None:
    videos = [fabriquer_video(identifiant=f"v{i}", compte=f"compte_{i}") for i in range(100)]
    fenetre = Fenetre(debut="2026-11-01T00:00:00+00:00", fin="2026-11-07T00:00:00+00:00")
    mesures = mesures_de_volume(videos, fenetre)
    assert all(m.echantillon.tronque and m.echantillon.resultats_consultes == 100 for m in mesures)
    assert not mesures_de_volume(videos[:99], fenetre)[0].echantillon.tronque


def test_mesure_sans_methode_echoue() -> None:
    fenetre = Fenetre(debut="2026-11-01T00:00:00+00:00", fin="2026-11-02T00:00:00+00:00")
    echantillon = mesures_de_volume([], fenetre)[0].echantillon
    with pytest.raises(ValueError):
        Mesure(nom="x", valeur=1, unite="u", methode="", fenetre=fenetre, echantillon=echantillon, source="s")


def test_aucun_mot_refuse_dans_les_textes_du_service(client: TestClient) -> None:
    _poser(*_trois_videos())
    for recit in client.get("/v1/radar").json()["recits"]:
        textes = [s["texte"] for s in recit["non_cherche"]] + [recit["requete_en_clair"]]
        for mesure in recit["mesures"]:
            textes += [mesure["methode"], mesure["unite"], mesure["source"], mesure["raison"] or ""]
        textes.append(recit["plus_ancienne_version"]["libelle"])
        assert all(contient_libelle_refuse(t) is None for t in textes)
        assert not any(mot in json.dumps(textes).lower() for mot in ("tendance", "viral", "sentiment"))


def test_fenetre_du_cas_reprise_sur_les_mesures(client: TestClient, tmp_path: Path) -> None:
    _poser(*_trois_videos())
    fenetre = {"debut": "2026-11-01T00:00:00+00:00", "fin": "2026-11-07T00:00:00+00:00"}
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A], "fenetre": fenetre})
    recit = client.get("/v1/radar").json()["recits"][0]
    assert all(m["fenetre"]["debut"].startswith("2026-11-01") for m in recit["mesures"])
