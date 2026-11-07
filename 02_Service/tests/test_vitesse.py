"""Vitesse (S06) : vidéos par jour sur 48 h et 7 jours, rapport, échantillon trop petit, tronqué."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import base
from app.libelles import contient_libelle_refuse
from app.recits import mesures_du_recit
from app.vitesse import mesures_de_vitesse
from tests.conftest import fabriquer_video

CALCULE_LE = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
PHRASE = "dix mille postes"


def _videos(*ages_en_heures: float, requete: str = PHRASE):
    return [
        fabriquer_video(
            identifiant=f"v-{i}",
            identifiant_plateforme=f"70000000000000{i:05d}",
            publie_le=(CALCULE_LE - timedelta(hours=h)).isoformat(),
            requetes_trouvees=[requete],
        )
        for i, h in enumerate(ages_en_heures)
    ]


def _par_nom(mesures):
    return {m.nom: m for m in mesures}


def test_valeurs_et_rapport_exacts():
    # 4 vidéos dans les 48 h, 3 de plus entre 2 et 7 jours, 1 hors des 7 jours
    videos = _videos(1, 10, 30, 47, 60, 100, 160, 200)
    m = _par_nom(mesures_de_vitesse(videos, CALCULE_LE))
    assert m["vitesse_48h"].valeur == 2.0  # 4 / 2
    assert m["vitesse_7j"].valeur == 1.0  # 7 / 7
    assert m["vitesse"].valeur == 2.0
    assert m["vitesse_48h"].fenetre.fin == CALCULE_LE
    assert m["vitesse_48h"].fenetre.debut == CALCULE_LE - timedelta(days=2)
    assert m["vitesse_7j"].fenetre.debut == CALCULE_LE - timedelta(days=7)
    for mesure in m.values():
        assert mesure.methode.strip() and mesure.raison is None


def test_deux_videos_valeur_nulle_avec_raison():
    m = _par_nom(mesures_de_vitesse(_videos(1, 5), CALCULE_LE))
    for mesure in m.values():
        assert mesure.valeur is None
        assert "échantillon trop petit" in (mesure.raison or "")


def test_fenetre_courte_vide_mais_longue_suffisante():
    m = _par_nom(mesures_de_vitesse(_videos(80, 100, 120, 150), CALCULE_LE))
    assert m["vitesse_48h"].valeur is None
    assert m["vitesse_7j"].valeur == round(4 / 7, 2)
    assert m["vitesse"].valeur is None and m["vitesse"].raison


def test_echantillon_tronque_dit_au_moins():
    videos = _videos(*([1.0] * 100))
    m = _par_nom(mesures_de_vitesse(videos, CALCULE_LE))
    assert m["vitesse_48h"].echantillon.tronque
    assert all("au moins" in x.methode for x in m.values())
    assert "au moins" not in _par_nom(mesures_de_vitesse(_videos(1, 2, 3), CALCULE_LE))["vitesse_7j"].methode


def test_aucun_mot_refuse():
    cas = [_videos(1, 5), _videos(1, 2, 3, 4, 90), _videos(*([1.0] * 100))]
    for videos in cas:
        for mesure in mesures_de_vitesse(videos, CALCULE_LE):
            texte = f"{mesure.nom} {mesure.unite} {mesure.methode} {mesure.raison or ''}"
            assert contient_libelle_refuse(texte) is None
            for mot in ("tendance", "monte", "viral"):
                assert mot not in texte.lower()


def test_mesures_du_recit_ajoute_vitesse_apres_volume():
    videos = _videos(1, 2, 3)
    from app.modeles import Fenetre

    noms = [m.nom for m in mesures_du_recit(videos, Fenetre(debut=CALCULE_LE, fin=CALCULE_LE), CALCULE_LE)]
    assert noms[:3] == ["videos_trouvees", "comptes_distincts", "vues_cumulees"]
    assert noms[3:] == ["vitesse_48h", "vitesse_7j", "vitesse"]


def test_radar_porte_la_vitesse(client: TestClient):
    for v in _videos(1, 2, 3, 4):
        base.ecrire("video", v.identifiant, "video.v1", v.model_dump(mode="json"))
    reponse = client.get("/v1/radar")
    assert reponse.status_code == 200
    for recit in reponse.json()["recits"]:
        noms = {m["nom"] for m in recit["mesures"]}
        assert {"vitesse_48h", "vitesse_7j", "vitesse"} <= noms
