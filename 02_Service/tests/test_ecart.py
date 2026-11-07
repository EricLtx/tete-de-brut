"""Écart au mot (S07) : opérations, positions, idempotence, contrat et durée."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import base
from app.ecart import comparer_mots, comparer_textes, identifiant_comparaison
from app.mots import normaliser
from tests.conftest import fabriquer_video

RACINE = Path(__file__).resolve().parent.parent


def poser(*videos) -> None:
    for v in videos:
        base.ecrire("video", v.identifiant, "video.v1", v.model_dump(mode="json"))


def demander(client: TestClient, source, reprise):
    return client.post(
        "/v1/comparaisons", json={"video_source": source.identifiant, "video_reprise": reprise.identifiant}
    )


def test_quatre_mots_retires_avec_positions() -> None:
    ops = comparer_textes(
        "Propos simulé : il faut dix mille postes si l'État paie",
        "Propos simulé : il faut dix mille postes",
    )
    assert len(ops) == 1
    op = ops[0]
    assert op.type == "retire"
    assert op.mots_source == ["si", "l", "état", "paie"]
    assert op.mots_reprise == []
    assert op.position_source == 7 and op.position_reprise == 7


def test_remplacement_et_ajout() -> None:
    ops = comparer_mots("a b c d".split(), "a x c d e".split())
    assert [o.type for o in ops] == ["remplace", "ajoute"]
    assert (ops[0].position_source, ops[0].position_reprise) == (1, 1)
    assert ops[0].mots_source == ["b"] and ops[0].mots_reprise == ["x"]
    assert (ops[1].position_source, ops[1].position_reprise) == (4, 4)
    assert ops[1].mots_reprise == ["e"]


def test_identiques_sans_operation() -> None:
    assert comparer_textes("Bonjour, le monde", "bonjour le monde") == []


def test_decimal_contre_entier_est_un_remplacement() -> None:
    ops = comparer_textes("3,5 milliards", "35 milliards")
    assert len(ops) == 1
    assert ops[0].type == "remplace"
    assert ops[0].mots_source == ["3,5"] and ops[0].mots_reprise == ["35"]


def test_application_des_operations_redonne_la_reprise() -> None:
    source = normaliser("un deux trois quatre cinq six sept")
    reprise = normaliser("un trois quatre huit cinq neuf dix sept onze")
    mots = list(source)
    for op in reversed(comparer_mots(source, reprise)):
        mots[op.position_source : op.position_source + len(op.mots_source)] = op.mots_reprise
    assert mots == reprise


def test_endpoint_operations_legende_et_texte_ecran(client: TestClient, deux_videos_comparables) -> None:
    source, reprise = deux_videos_comparables
    poser(source, reprise)
    r = demander(client, source, reprise)
    assert r.status_code == 200
    corps = r.json()
    assert corps["normalisation"] == "mots.v1"
    assert corps["operations"][0]["type"] == "retire"
    assert corps["operations"][0]["mots_source"] == ["si", "l", "état", "paie"]
    assert corps["ecart_legende"][0]["mots_source"] == ["source"]
    assert corps["ecart_legende"][0]["mots_reprise"] == ["reprise"]
    assert corps["ecart_texte_ecran"][0]["type"] == "remplace"
    assert corps["ecart_texte_ecran"][0]["mots_source"] == ["10", "000"]
    assert corps["transcriptions"]["source"]["source"] == "Oriane"
    assert corps["transcriptions"]["reprise"]["niveau"] == "default"
    assert corps["heure_dans_la_video"] == {"secondes": None, "libelle": "non fournie au niveau default"}
    assert corps["mode"] == "enregistre" and corps["enregistre_le"]


def test_deux_post_rendent_le_meme_corps(client: TestClient, deux_videos_comparables) -> None:
    source, reprise = deux_videos_comparables
    poser(source, reprise)
    a, b = demander(client, source, reprise), demander(client, source, reprise)
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()
    assert a.json()["identifiant"] == identifiant_comparaison(source.identifiant, reprise.identifiant)
    assert demander(client, reprise, source).json()["identifiant"] != a.json()["identifiant"]


def test_get_puis_404(client: TestClient, deux_videos_comparables) -> None:
    source, reprise = deux_videos_comparables
    poser(source, reprise)
    cree = demander(client, source, reprise).json()
    lu = client.get(f"/v1/comparaisons/{cree['identifiant']}")
    assert lu.status_code == 200 and lu.json() == cree
    absent = client.get("/v1/comparaisons/cmp-absent")
    assert absent.status_code == 404 and absent.json()["erreur"] == "introuvable"


def test_video_inconnue_404_et_identiques_422(client: TestClient) -> None:
    poser(fabriquer_video(identifiant="v-seule"))
    r = client.post("/v1/comparaisons", json={"video_source": "v-seule", "video_reprise": "v-absente"})
    assert r.status_code == 404 and r.json()["erreur"] == "introuvable"
    r = client.post("/v1/comparaisons", json={"video_source": "v-seule", "video_reprise": "v-seule"})
    assert r.status_code == 422


def _conforme(valeur, schema, defs) -> None:
    """Validation minimale contre le schéma (jsonschema n'est pas une dépendance du service)."""
    if "$ref" in schema:
        schema = defs[schema["$ref"].rsplit("/", 1)[1]]
    if "const" in schema:
        assert valeur == schema["const"]
    if "enum" in schema:
        assert valeur in schema["enum"]
    if schema.get("type") == "object":
        assert isinstance(valeur, dict)
        proprietes = schema["properties"]
        assert set(valeur) <= set(proprietes), set(valeur) - set(proprietes)
        assert set(schema.get("required", [])) <= set(valeur)
        for nom, sous in valeur.items():
            _conforme(sous, proprietes[nom], defs)
    elif schema.get("type") == "array":
        assert isinstance(valeur, list)
        for element in valeur:
            _conforme(element, schema["items"], defs)
    elif schema.get("type") == "string" and valeur is not None:
        assert isinstance(valeur, str)
    elif schema.get("type") == "integer":
        assert isinstance(valeur, int) and valeur >= schema.get("minimum", valeur)


def test_conforme_au_schema(client: TestClient, deux_videos_comparables) -> None:
    source, reprise = deux_videos_comparables
    poser(source, reprise)
    corps = demander(client, source, reprise).json()
    schema = json.loads((RACINE / "contrats" / "ecart.v1.schema.json").read_text(encoding="utf-8"))
    _conforme(corps, schema, schema["$defs"])
    assert set(corps) == set(schema["properties"])


def test_duree_600_contre_150_mots() -> None:
    source = [f"mot{i % 97}" for i in range(600)]
    reprise = [f"mot{(i * 3) % 89}" for i in range(150)]
    debut = time.perf_counter()
    comparer_mots(source, reprise)
    assert time.perf_counter() - debut < 0.5


@pytest.mark.parametrize("texte", ["", "   "])
def test_textes_vides(texte: str) -> None:
    assert comparer_textes(texte, "un mot")[0].type == "ajoute"
