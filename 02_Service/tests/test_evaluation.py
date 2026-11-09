"""Banc d'évaluation (S22) : métriques exactes, jeu `jeu.v1`, rapport en comptes, bras, Git.

Aucun réseau : le service est joué par `TestClient`, Oriane par `httpx.MockTransport` (`tests/conftest.py`).
Le jeu est simulé (identifiants et textes fictifs) ; aucune question réelle n'entre dans le dépôt.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import creer_application
from evaluation import metriques
from evaluation.metriques import (
    JeuInvalide,
    fait_couvert,
    faits_couverts,
    ndcg_a_k,
    rappel_a_k,
    valider_jeu,
)
from tests.conftest import construire_config

RACINE_SERVICE = Path(__file__).resolve().parent.parent
ID_1 = "cnt_SIMULE0000000000000000000001"
ID_2 = "cnt_SIMULE0000000000000000000002"
CLE_ORIANE_TEST = "cle-fictive-pour-les-tests-0001"


def _charger_script() -> Any:
    spec = importlib.util.spec_from_file_location("evaluer", RACINE_SERVICE / "scripts/evaluer.py")
    script = importlib.util.module_from_spec(spec)
    sys.modules["evaluer"] = script  # nécessaire aux dataclasses du script
    spec.loader.exec_module(script)
    return script


evaluer = _charger_script()


# --- rappel@k et nDCG@k sur des listes connues -------------------------------------------------------


def test_rappel_sur_une_liste_connue() -> None:
    rendues = ["a", "b", "c", "d"]
    pertinentes = ["b", "d", "z"]
    assert rappel_a_k(rendues, pertinentes, 1) == 0.0
    assert rappel_a_k(rendues, pertinentes, 2) == pytest.approx(1 / 3)
    assert rappel_a_k(rendues, pertinentes, 4) == pytest.approx(2 / 3)
    assert rappel_a_k(rendues, pertinentes, 50) == pytest.approx(2 / 3)  # k au-delà de la liste
    assert rappel_a_k(["z", "b", "d"], pertinentes, 3) == 1.0
    assert rappel_a_k([], pertinentes, 3) == 0.0


def test_rappel_ne_compte_pas_deux_fois_une_video_rendue_deux_fois() -> None:
    assert rappel_a_k(["b", "b", "b"], ["b", "d"], 3) == 0.5


def test_ndcg_sur_des_listes_connues() -> None:
    # Toutes les pertinentes en tête : 1.
    assert ndcg_a_k(["a", "c", "x"], ["a", "c"], 3) == pytest.approx(1.0)
    # Une seule pertinente, au rang 2 : 1 / log2(3).
    assert ndcg_a_k(["x", "a"], ["a"], 2) == pytest.approx(1 / math.log2(3))
    # Pertinentes aux rangs 1 et 3 sur deux attendues : (1 + 1/2) / (1 + 1/log2(3)).
    attendu = (1 + 1 / 2) / (1 + 1 / math.log2(3))
    assert ndcg_a_k(["a", "x", "c"], ["a", "c"], 3) == pytest.approx(attendu)
    assert attendu == pytest.approx(0.9197, abs=1e-4)
    # Rien de pertinent dans les k premiers : 0 ; une pertinente rendue au-delà de k ne compte pas.
    assert ndcg_a_k(["x", "y", "a"], ["a"], 2) == 0.0


def test_ndcg_ignore_les_rendus_en_double_et_borne_k() -> None:
    assert ndcg_a_k(["a", "a", "a"], ["a", "c"], 3) == pytest.approx(1 / (1 + 1 / math.log2(3)))
    # Plus de pertinentes que de places : l'idéal est borné par k.
    assert ndcg_a_k(["a", "b"], ["a", "b", "c", "d"], 2) == pytest.approx(1.0)


@pytest.mark.parametrize("k", [0, -1, True, 2.5])
def test_k_invalide_refuse(k: Any) -> None:
    with pytest.raises(ValueError):
        rappel_a_k(["a"], ["a"], k)
    with pytest.raises(ValueError):
        ndcg_a_k(["a"], ["a"], k)


def test_sans_video_pertinente_les_metriques_sont_refusees() -> None:
    with pytest.raises(ValueError):
        rappel_a_k(["a"], [], 3)
    with pytest.raises(ValueError):
        ndcg_a_k(["a"], [], 3)


# --- faits couverts ---------------------------------------------------------------------------------


def test_fait_couvert_ignore_casse_accents_et_ponctuation() -> None:
    textes = ["Propos simulé : il faut dix mille postes si l'État paie", "TEXTE SIMULÉ : 10 000 postes"]
    assert fait_couvert("si l'etat paie", textes)
    assert fait_couvert("SI L’ÉTAT PAIE", textes)  # apostrophe typographique
    assert fait_couvert("10 000 postes", textes)
    assert not fait_couvert("vingt mille postes", textes)
    assert not fait_couvert("poste", textes)  # un mot entier, pas un fragment de mot
    assert not fait_couvert("   ", textes)
    assert not fait_couvert("dix mille", [])


def test_faits_couverts_compte_les_faits_retrouves() -> None:
    textes = ["dix mille postes", "si l'État paie"]
    assert faits_couverts(["dix mille postes", "si l'État paie", "avant 2027"], textes) == 2
    assert faits_couverts([], textes) == 0


# --- jeu jeu.v1 ------------------------------------------------------------------------------------


def jeu_simule() -> dict[str, Any]:
    """Jeu simulé de trois questions : identifiants et textes fictifs."""
    return {
        "version": "jeu.v1",
        "nom": "jeu simulé",
        "budget_credits_reference": 45,
        "questions": [
            {
                "id": "q1",
                "question": "« dix mille postes »",
                "faits_attendus": ["dix mille postes", "si l'État paie"],
                "videos_pertinentes": [ID_1, ID_2],
            },
            {
                "id": "q2",
                "question": "« dix mille postes » depuis 3 jours",
                "faits_attendus": ["10 000 postes", "avant 2027"],
                "videos_pertinentes": [ID_2, "cnt_ABSENTE"],
            },
            {
                "id": "q3",
                "question": "« autre phrase simulée »",
                "faits_attendus": ["fait introuvable"],
                "videos_pertinentes": ["cnt_ABSENTE_2"],
            },
        ],
    }


def test_jeu_valide_est_accepte() -> None:
    jeu = valider_jeu(jeu_simule())
    assert jeu.nom == "jeu simulé"
    assert jeu.budget_credits_reference == 45
    assert [q.identifiant for q in jeu.questions] == ["q1", "q2", "q3"]
    assert jeu.questions[0].faits_attendus == ("dix mille postes", "si l'État paie")


def _sans(document: dict[str, Any], *chemin: str) -> dict[str, Any]:
    cible: Any = document
    for cle in chemin[:-1]:
        cible = cible[int(cle)] if isinstance(cible, list) else cible[cle]
    del cible[chemin[-1]]
    return document


def _avec(document: dict[str, Any], valeur: Any, *chemin: str) -> dict[str, Any]:
    cible: Any = document
    for cle in chemin[:-1]:
        cible = cible[int(cle)] if isinstance(cible, list) else cible[cle]
    cible[chemin[-1]] = valeur
    return document


@pytest.mark.parametrize(
    ("document", "morceau"),
    [
        ("pas un objet", "objet attendu"),
        (_avec(jeu_simule(), "jeu.v2", "version"), "jeu.v1"),
        (_sans(jeu_simule(), "nom"), "manquant"),
        (_avec(jeu_simule(), "x", "extra"), "inconnu"),
        (_avec(jeu_simule(), "  ", "nom"), "nom"),
        (_avec(jeu_simule(), -1, "budget_credits_reference"), "budget"),
        (_avec(jeu_simule(), "45", "budget_credits_reference"), "budget"),
        (_avec(jeu_simule(), True, "budget_credits_reference"), "budget"),
        (_avec(jeu_simule(), [], "questions"), "au moins une question"),
        (_sans(jeu_simule(), "questions", "0", "faits_attendus"), "manquant"),
        (_avec(jeu_simule(), [], "questions", "0", "faits_attendus"), "faits_attendus"),
        (_avec(jeu_simule(), ["a", "b", "c", "d"], "questions", "0", "faits_attendus"), "1 à 3"),
        (_avec(jeu_simule(), ["a", "a"], "questions", "0", "faits_attendus"), "doublon"),
        (_avec(jeu_simule(), [], "questions", "0", "videos_pertinentes"), "videos_pertinentes"),
        (_avec(jeu_simule(), [3], "questions", "0", "videos_pertinentes"), "texte non vide"),
        (_avec(jeu_simule(), "", "questions", "0", "question"), "question"),
        (_avec(jeu_simule(), "x" * 1001, "questions", "0", "question"), "1000"),
        (_avec(jeu_simule(), "q2", "questions", "0", "id"), "en double"),
    ],
)
def test_jeu_mal_forme_refuse(document: Any, morceau: str) -> None:
    with pytest.raises(JeuInvalide, match=re.escape(morceau)):
        valider_jeu(document)


def test_le_schema_et_le_validateur_disent_la_meme_chose() -> None:
    schema = json.loads((RACINE_SERVICE / "evaluation/jeu.v1.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == metriques.CLES_JEU == set(schema["properties"])
    question = schema["$defs"]["Question"]
    assert set(question["required"]) == metriques.CLES_QUESTION == set(question["properties"])
    assert question["properties"]["faits_attendus"]["minItems"] == metriques.FAITS_MIN
    assert question["properties"]["faits_attendus"]["maxItems"] == metriques.FAITS_MAX
    assert question["properties"]["question"]["maxLength"] == metriques.QUESTION_MAX
    assert schema["properties"]["version"]["const"] == metriques.VERSION_JEU
    # Le jeu simulé tient dans le schéma : mêmes clés, mêmes bornes.
    document = jeu_simule()
    assert set(document) == set(schema["required"])
    for q in document["questions"]:
        assert set(q) == set(question["required"])


# --- Git : le dossier de données du banc est ignoré --------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git absent")
def test_le_dossier_de_donnees_du_banc_est_ignore_par_git() -> None:
    def ignore(chemin: str) -> bool:
        resultat = subprocess.run(
            ["git", "check-ignore", "-q", chemin], cwd=RACINE_SERVICE, capture_output=True, check=False
        )
        assert resultat.returncode in (0, 1), resultat.stderr
        return resultat.returncode == 0

    assert ignore("evaluation/donnees/jeu-or.json")
    assert ignore("evaluation/donnees/rapport-unique-20261109-120000.txt")
    # Le code, le schéma et le mode d'emploi, eux, restent versionnés.
    assert not ignore("evaluation/metriques.py")
    assert not ignore("evaluation/jeu.v1.schema.json")
    assert not ignore("evaluation/README.md")


# --- bras unique contre le service, sans réseau ------------------------------------------------------


@pytest.fixture
def service_direct(
    tmp_path: Path, transport_oriane_simule: Callable[..., httpx.MockTransport]
) -> Iterator[tuple[TestClient, httpx.MockTransport]]:
    """Service en direct (clé fictive), Oriane simulée : la même réponse à chaque recherche."""
    transport = transport_oriane_simule()
    config = construire_config(tmp_path, ORIANE_API_KEY=CLE_ORIANE_TEST)
    with TestClient(creer_application(config)) as client:
        client.app.state.transport_oriane = transport
        yield client, transport


def _ecrire_jeu(tmp_path: Path, document: dict[str, Any] | None = None) -> Path:
    chemin = tmp_path / "jeu-simule.json"
    chemin.write_text(json.dumps(document or jeu_simule(), ensure_ascii=False), encoding="utf-8")
    return chemin


def test_jeu_simule_de_trois_questions_donne_un_rapport_lisible(
    service_direct: tuple[TestClient, httpx.MockTransport], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client, transport = service_direct
    sortie = tmp_path / "donnees"
    code = evaluer.main(
        ["--jeu", str(_ecrire_jeu(tmp_path)), "--bras", "unique", "--sortie", str(sortie)], client=client
    )
    assert code == 0
    texte = capsys.readouterr().out
    # Trois recherches, une par question, vers Oriane simulée seulement.
    assert len(transport.requetes) == 3  # type: ignore[attr-defined]
    assert "bras unique" in texte and "3 question(s)" in texte and "k = 10" in texte
    # q1 : les deux pertinentes retrouvées, les deux faits couverts.
    assert re.search(r"- q1 : rappel@10 2/2, nDCG@10 1\.00, faits 2/2, crédits 15", texte)
    # q2 : une pertinente sur deux (l'autre n'existe pas) ; « 10 000 postes » couvert, « avant 2027 » non.
    assert re.search(r"- q2 : rappel@10 1/2, nDCG@10 0\.\d\d, faits 1/2, crédits 15", texte)
    # q3 : rien de pertinent, aucun fait.
    assert re.search(r"- q3 : rappel@10 0/1, nDCG@10 0\.00, faits 0/1, crédits 15", texte)
    # Synthèse en comptes.
    assert "questions répondues par le service : 3 sur 3" in texte
    assert "dont toutes les vidéos pertinentes sont dans les 10 premières : 1 sur 3" in texte
    assert "au moins une vidéo pertinente dans les 10 premières : 2 sur 3" in texte
    assert "vidéos pertinentes retrouvées : 3 sur 5" in texte
    assert "tous les faits attendus sont couverts : 1 sur 3" in texte
    assert "faits couverts : 3 sur 5" in texte
    assert "crédits dépensés : 45 (référence du jeu : 45)" in texte
    assert "jetons : non mesurés" in texte
    assert "latence : médiane" in texte
    # Un contrôle de cohérence, jamais une inférence statistique.
    assert "pas une inférence statistique" in texte
    for mot in ("significatif", "p-valeur", "intervalle de confiance", "p <"):
        assert mot not in texte
    # Aucun compte, aucun texte de question dans le rapport.
    assert "compte_simule" not in texte and "dix mille postes »" not in texte
    # Rapport écrit dans le dossier demandé, en lisible et en JSON.
    ecrits = sorted(p.name for p in sortie.iterdir())
    assert len(ecrits) == 2 and ecrits[0].startswith("rapport-unique-")
    assert ecrits[0].endswith(".json") and ecrits[1].endswith(".txt")
    donnees = json.loads((sortie / ecrits[0]).read_text(encoding="utf-8"))
    assert donnees["bras"] == "unique" and [q["identifiant"] for q in donnees["questions"]] == [
        "q1",
        "q2",
        "q3",
    ]
    assert (sortie / ecrits[1]).read_text(encoding="utf-8").strip() == texte.split("rapport écrit")[0].strip()


def test_une_question_sans_reponse_du_service_est_comptee_pas_cachee(
    service_direct: tuple[TestClient, httpx.MockTransport], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client, _ = service_direct
    document = jeu_simule()
    document["questions"][2]["question"] = "Dupont"  # nom seul : refusé par RG-02 (422)
    code = evaluer.main(
        ["--jeu", str(_ecrire_jeu(tmp_path, document)), "--bras", "unique", "--sortie", str(tmp_path / "s")],
        client=client,
    )
    assert code == 0
    texte = capsys.readouterr().out
    assert "- q3 : sans réponse du service (422 validation)" in texte
    assert "questions répondues par le service : 2 sur 3" in texte
    assert "dont toutes les vidéos pertinentes sont dans les 10 premières : 1 sur 3" in texte


def test_le_mode_enregistre_ne_depense_aucun_credit(
    client: TestClient, tmp_path: Path, cas_simule: Callable[..., Path]
) -> None:
    cas_simule(client.app.state.config)
    document = jeu_simule()
    document["questions"] = document["questions"][:1]
    document["questions"][0]["question"] = "« dix mille postes »"
    jeu = evaluer.charger_jeu(_ecrire_jeu(tmp_path, document))
    (resultat,) = evaluer.evaluer(client, jeu, "unique", 10)
    assert resultat.mode == "enregistre" and resultat.echec == ""
    assert resultat.credits == 0
    assert resultat.rendues


@pytest.mark.parametrize("bras", ["multi", "boucle"])
def test_les_bras_multi_et_boucle_sont_refuses_proprement(
    bras: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    appels: list[httpx.Request] = []

    def repondre(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        return httpx.Response(500)

    with httpx.Client(base_url="http://service.invalid", transport=httpx.MockTransport(repondre)) as client:
        code = evaluer.main(["--jeu", str(_ecrire_jeu(tmp_path)), "--bras", bras], client=client)
    sortie = capsys.readouterr()
    assert code == 2
    assert "disponible à partir de S29" in sortie.err and bras in sortie.err
    assert appels == []  # refusé avant tout appel


def test_un_bras_inconnu_est_refuse_par_la_ligne_de_commande(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as sortie:
        evaluer.main(["--jeu", str(_ecrire_jeu(tmp_path)), "--bras", "autre"])
    assert sortie.value.code == 2


def test_un_jeu_mal_forme_arrete_le_script_sans_appel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = jeu_simule()
    document["questions"][0]["faits_attendus"] = []
    assert evaluer.main(["--jeu", str(_ecrire_jeu(tmp_path, document)), "--bras", "unique"]) == 2
    assert "jeu refusé" in capsys.readouterr().err
    illisible = tmp_path / "jeu-casse.json"
    illisible.write_text("{pas du json", encoding="utf-8")
    assert evaluer.main(["--jeu", str(illisible), "--bras", "unique"]) == 2
    assert evaluer.main(["--jeu", str(tmp_path / "absent.json"), "--bras", "unique"]) == 2
    assert evaluer.main(["--jeu", str(_ecrire_jeu(tmp_path)), "--bras", "unique", "--k", "0"]) == 2


def test_un_service_injoignable_donne_le_code_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def couper(requete: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("coupé", request=requete)

    with httpx.Client(base_url="http://service.invalid", transport=httpx.MockTransport(couper)) as client:
        code = evaluer.main(["--jeu", str(_ecrire_jeu(tmp_path)), "--bras", "unique"], client=client)
    assert code == 1
    assert "service injoignable" in capsys.readouterr().err
