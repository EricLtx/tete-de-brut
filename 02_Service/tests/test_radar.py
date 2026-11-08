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
from tests.conftest import CLE_DEMO_TEST, fabriquer_video

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
    volumes = [m for m in recit["mesures"] if not m["nom"].startswith("vitesse")]  # la vitesse a ses fenêtres
    assert volumes and all(m["fenetre"]["debut"].startswith("2026-11-01") for m in volumes)


@pytest.mark.parametrize(
    ("cas", "morceau"),
    [
        ({"phrases": [PHRASE_A], "enregistre_le": "2026-11-07T08:00:00"}, "fuseau"),
        (
            {
                "phrases": [PHRASE_A],
                "fenetre": {"debut": "2026-11-07T00:00:00+00:00", "fin": "2026-11-01T00:00:00+00:00"},
            },
            "illisible",
        ),
        ({"phrases": PHRASE_A}, "phrases"),
    ],
    ids=["enregistre_le_sans_fuseau", "fenetre_inversee", "phrases_en_chaine"],
)
def test_cas_mal_forme_ignore_et_dit(client: TestClient, cas: dict, morceau: str) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-mal-forme", "cas.v1", cas)
    reponse = client.get("/v1/radar")
    assert reponse.status_code == 200
    recits = reponse.json()["recits"]
    assert len(recits) == 2  # repli sur les requêtes des vidéos
    mentions = [s["texte"] for s in recits[0]["non_cherche"] if s["texte"].startswith("cas ignoré : ")]
    assert len(mentions) == 1 and morceau in mentions[0]
    assert client.get(f"/v1/recits/{recits[0]['identifiant']}").status_code == 200


# --- suppression d'un récit (F019) ---


def _id_recit(client: TestClient, phrase: str) -> str:
    recits = client.get("/v1/radar").json()["recits"]
    return next(r["identifiant"] for r in recits if r["phrase_surveillee"] == phrase)


def test_suppression_retire_le_recit_ses_phrases_et_ses_videos_orphelines(client: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A, PHRASE_B]})
    base.ecrire("cas", "recherche-x", "cas.v1", {"phrases": [PHRASE_A], "requete": "requête de recherche"})
    identifiant = _id_recit(client, PHRASE_A)
    reponse = client.delete(f"/v1/recits/{identifiant}")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["identifiant"] == identifiant and corps["phrase_surveillee"] == PHRASE_A
    assert corps["videos_retirees"] == 2 and corps["videos_conservees"] == 0
    assert corps["mode"] == "enregistre" and corps["enregistre_le"]
    assert corps["avertissement"] and "redémarrage" in corps["avertissement"]
    assert [r["phrase_surveillee"] for r in client.get("/v1/radar").json()["recits"]] == [PHRASE_B]
    assert client.get(f"/v1/recits/{identifiant}").status_code == 404
    assert base.lire("cas", "recherche-x") is None  # document ajouté par une recherche, vidé : supprimé
    assert base.lire("cas", "cas-1")["phrases"] == [PHRASE_B]
    assert sorted(d["identifiant"] for d in base.lister("video")) == ["v-b"]


def test_suppression_garde_la_video_trouvee_par_une_autre_phrase(client: TestClient) -> None:
    _poser(
        fabriquer_video(identifiant="v-double", requetes_trouvees=[PHRASE_A, PHRASE_B]),
        fabriquer_video(identifiant="v-seule", compte="compte_simule_b", requetes_trouvees=[PHRASE_A]),
    )
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A, PHRASE_B]})
    corps = client.delete(f"/v1/recits/{_id_recit(client, PHRASE_A)}").json()
    assert corps["videos_retirees"] == 1 and corps["videos_conservees"] == 1
    restantes = {d["identifiant"]: d for d in base.lister("video")}
    assert list(restantes) == ["v-double"]
    assert restantes["v-double"]["requetes_trouvees"] == [PHRASE_B]
    recits = client.get("/v1/radar").json()["recits"]
    assert [(r["phrase_surveillee"], r["videos"]) for r in recits] == [(PHRASE_B, ["v-double"])]


def test_suppression_phrase_unique_du_cas_et_phrases_voisines_intactes(client: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrase": PHRASE_A})
    base.ecrire("cas", "cas-2", "cas.v1", {"phrases": [PHRASE_B]})
    client.delete(f"/v1/recits/{_id_recit(client, PHRASE_A)}")
    assert base.lire("cas", "cas-1") is None
    assert base.lire("cas", "cas-2") == {"phrases": [PHRASE_B]}


def test_suppression_recit_inconnu_rend_404(client: TestClient) -> None:
    reponse = client.delete("/v1/recits/recit-inconnu")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"] == "introuvable"
    assert reponse.json()["mode"] == "enregistre"


def test_suppression_est_consignee_au_journal(client: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A]})
    client.delete(f"/v1/recits/{_id_recit(client, PHRASE_A)}")
    entrees = [e for e in client.get("/v1/journal").json()["entrees"] if e["route"] == "recit:suppression"]
    assert len(entrees) == 1
    assert entrees[0]["cible"] == PHRASE_A
    assert entrees[0]["resultats"] == {"videos_retirees": 2, "videos_conservees": 0}
    assert entrees[0]["mode"] == "enregistre"


def test_suppression_sans_cle_ne_supprime_rien(client_avec_cle: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A]})
    identifiant = _id_recit(client_avec_cle, PHRASE_A)
    refus = client_avec_cle.delete(f"/v1/recits/{identifiant}")
    assert refus.status_code == 401 and refus.json()["erreur"] == "cle_demo_invalide"
    assert client_avec_cle.get(f"/v1/recits/{identifiant}").status_code == 200
    ouvert = client_avec_cle.delete(f"/v1/recits/{identifiant}", headers={"X-Cle-Demo": CLE_DEMO_TEST})
    assert ouvert.status_code == 200
    assert client_avec_cle.get(f"/v1/recits/{identifiant}").status_code == 404


def test_suppression_reponse_sans_libelle_refuse(client: TestClient) -> None:
    _poser(*_trois_videos())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_A]})
    corps = client.delete(f"/v1/recits/{_id_recit(client, PHRASE_A)}").json()
    assert contient_libelle_refuse(corps["avertissement"]) is None


# --- une recherche = un récit, variantes comprises (F020) ---

NOYAU = "pouvoir achat"
VARIANTE_EXACTE = "le pouvoir d'achat"
AUTRE_VARIANTE = "fin du mois difficile"


def _poser_recherche(
    identifiant: str = "recherche-x", pivot: str = NOYAU, variantes: list[str] | None = None
):
    base.ecrire(
        "cas",
        identifiant,
        "cas.v1",
        {
            "pivot": pivot,
            "variantes": variantes or [NOYAU, VARIANTE_EXACTE, AUTRE_VARIANTE],
            "noyaux": [NOYAU],
            "requete": "requête de recherche",
        },
    )


def _videos_de_recherche():
    return (
        fabriquer_video(
            identifiant="v-deux-variantes",
            publie_le="2026-11-03T10:00:00+00:00",
            requetes_trouvees=[NOYAU, VARIANTE_EXACTE],
        ),
        fabriquer_video(
            identifiant="v-noyau",
            compte="compte_simule_b",
            publie_le="2026-11-04T10:00:00+00:00",
            requetes_trouvees=[NOYAU],
        ),
        fabriquer_video(
            identifiant="v-fin-du-mois",
            compte="compte_simule_c",
            publie_le="2026-11-05T10:00:00+00:00",
            requetes_trouvees=[AUTRE_VARIANTE],
        ),
        fabriquer_video(
            identifiant="v-ailleurs",
            compte="compte_simule_d",
            publie_le="2026-11-06T10:00:00+00:00",
            requetes_trouvees=[PHRASE_B],
        ),
    )


def test_une_recherche_est_un_seul_recit_et_une_video_trouvee_deux_fois_compte_une_fois(
    client: TestClient,
) -> None:
    _poser(*_videos_de_recherche())
    _poser_recherche()
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_B]})
    recits = {r["phrase_surveillee"]: r for r in client.get("/v1/radar").json()["recits"]}
    assert set(recits) == {NOYAU, PHRASE_B}
    recit = recits[NOYAU]
    assert recit["variantes"] == [NOYAU, VARIANTE_EXACTE, AUTRE_VARIANTE]
    assert recit["videos"] == ["v-deux-variantes", "v-noyau", "v-fin-du-mois"]  # union, sans doublon
    assert _mesure(recit, "videos_trouvees")["valeur"] == 3
    assert recit["requete_en_clair"] == "requête de recherche"
    assert recits[PHRASE_B]["variantes"] is None  # la phrase d'un cas n'a pas de variantes
    assert recits[PHRASE_B]["sous_recherches"] is None
    assert [(s["libelle"], s["type"], s["videos"]) for s in recit["sous_recherches"]] == [
        (NOYAU, "mots", 2),
        (VARIANTE_EXACTE, "exacte", 1),
        (AUTRE_VARIANTE, "exacte", 1),
    ]
    _valider_recit(recit)
    assert client.get(f"/v1/recits/{recit['identifiant']}").json()["variantes"] == recit["variantes"]


def test_sous_recherches_comptent_chaque_variante_et_le_total_reste_l_union(client: TestClient) -> None:
    # Deux variantes, une vidéo commune : 2 et 1 vidéos par variante, total 2 (la commune compte une fois).
    _poser(
        fabriquer_video(identifiant="v-commune", requetes_trouvees=[NOYAU, VARIANTE_EXACTE]),
        fabriquer_video(identifiant="v-noyau", compte="compte_simule_b", requetes_trouvees=[NOYAU]),
    )
    _poser_recherche(variantes=[NOYAU, VARIANTE_EXACTE])
    (recit,) = client.get("/v1/radar").json()["recits"]
    assert recit["sous_recherches"] == [
        {"libelle": NOYAU, "type": "mots", "videos": 2},
        {"libelle": VARIANTE_EXACTE, "type": "exacte", "videos": 1},
    ]
    assert len(recit["videos"]) == 2 and _mesure(recit, "videos_trouvees")["valeur"] == 2
    _valider_recit(recit)


def test_une_recherche_sans_resultat_reste_au_radar_avec_ses_variantes(client: TestClient) -> None:
    _poser_recherche()
    (recit,) = client.get("/v1/radar").json()["recits"]
    assert recit["videos"] == [] and recit["variantes"] == [NOYAU, VARIANTE_EXACTE, AUTRE_VARIANTE]
    assert _mesure(recit, "videos_trouvees")["valeur"] == 0


def test_le_pivot_d_une_recherche_egal_a_une_phrase_du_cas_garde_la_priorite_du_cas(
    client: TestClient,
) -> None:
    _poser(*_videos_de_recherche())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [NOYAU], "requete": "requête de cas lisible"})
    _poser_recherche()  # écrit après : le pivot est la même clé que la phrase du cas
    (recit,) = client.get("/v1/radar").json()["recits"]
    assert recit["requete_en_clair"] == "requête de cas lisible"
    assert recit["variantes"] == [NOYAU, VARIANTE_EXACTE, AUTRE_VARIANTE]
    assert len(recit["videos"]) == 3


def test_le_cas_ecrit_apres_la_recherche_prend_aussi_la_priorite(client: TestClient) -> None:
    _poser_recherche("a-recherche")
    base.ecrire(
        "cas", "z-cas", "cas.v1", {"phrases": ["Pouvoir  Achat"], "requete": "requête de cas lisible"}
    )
    (recit,) = client.get("/v1/radar").json()["recits"]
    assert recit["phrase_surveillee"] == "Pouvoir  Achat"
    assert recit["requete_en_clair"] == "requête de cas lisible"
    assert recit["variantes"][0] == NOYAU


def test_deux_cles_differentes_restent_deux_recits(client: TestClient) -> None:
    _poser(*_videos_de_recherche())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [VARIANTE_EXACTE]})
    _poser_recherche()
    recits = {r["phrase_surveillee"]: r for r in client.get("/v1/radar").json()["recits"]}
    assert set(recits) == {VARIANTE_EXACTE, NOYAU}
    assert recits[VARIANTE_EXACTE]["videos"] == ["v-deux-variantes"]
    assert len(recits[NOYAU]["videos"]) == 3


@pytest.mark.parametrize(
    "document",
    [
        {"pivot": 3, "variantes": [NOYAU]},
        {"pivot": NOYAU, "variantes": NOYAU},
        {"pivot": NOYAU, "variantes": [NOYAU, ""]},
    ],
)
def test_recherche_mal_formee_ignoree(client: TestClient, document: dict) -> None:
    base.ecrire("cas", "recherche-x", "cas.v1", document)
    assert client.get("/v1/radar").json()["recits"] == []


def test_suppression_d_un_recit_a_variantes_retire_toutes_ses_variantes(client: TestClient) -> None:
    _poser(*_videos_de_recherche())
    _poser(
        fabriquer_video(
            identifiant="v-aussi-b", compte="compte_simule_e", requetes_trouvees=[NOYAU, PHRASE_B]
        )
    )
    _poser_recherche()
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [PHRASE_B]})
    identifiant = _id_recit(client, NOYAU)
    corps = client.delete(f"/v1/recits/{identifiant}").json()
    assert corps["phrase_surveillee"] == NOYAU
    assert corps["videos_retirees"] == 3 and corps["videos_conservees"] == 1
    assert base.lire("cas", "recherche-x") is None
    assert base.lire("cas", "cas-1")["phrases"] == [PHRASE_B]
    restantes = {d["identifiant"]: d["requetes_trouvees"] for d in base.lister("video")}
    assert restantes == {"v-ailleurs": [PHRASE_B], "v-aussi-b": [PHRASE_B]}
    assert [r["phrase_surveillee"] for r in client.get("/v1/radar").json()["recits"]] == [PHRASE_B]
    assert client.get(f"/v1/recits/{identifiant}").status_code == 404


def test_suppression_d_un_recit_a_variantes_garde_la_phrase_d_un_autre_recit(client: TestClient) -> None:
    _poser(*_videos_de_recherche())
    base.ecrire("cas", "cas-1", "cas.v1", {"phrases": [VARIANTE_EXACTE]})
    _poser_recherche()
    corps = client.delete(f"/v1/recits/{_id_recit(client, NOYAU)}").json()
    # `le pouvoir d'achat` est aussi la phrase d'un autre récit : elle reste sur sa vidéo.
    assert corps["videos_retirees"] == 2 and corps["videos_conservees"] == 1
    restantes = {d["identifiant"]: d["requetes_trouvees"] for d in base.lister("video")}
    assert restantes == {"v-deux-variantes": [VARIANTE_EXACTE], "v-ailleurs": [PHRASE_B]}
    (recit,) = client.get("/v1/radar").json()["recits"]
    assert recit["phrase_surveillee"] == VARIANTE_EXACTE and recit["videos"] == ["v-deux-variantes"]
