"""Contrats (S02) : normalisation `mots.v1`, libellés refusés, modèles, schémas exportés, routes en 501."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.libelles import LIBELLES_REFUSES, contient_libelle_refuse
from app.main import creer_application, routeur_v1
from app.modeles import (
    CONTRATS,
    LIBELLE_PLUS_ANCIENNE_VERSION,
    LIMITE_TRANSCRIPTIONS,
    Decision,
    DemandeComparaison,
    Ecart,
    Fiche,
    Mesure,
    Operation,
    Recit,
    Segment,
    schema_contrat,
)
from app.mots import normaliser
from tests.conftest import CHAMPS_TIERS_ORIANE, ENREGISTRE_LE_TEST, LUE_LE_TEST, fabriquer_video

RACINE_SERVICE = Path(__file__).resolve().parent.parent
DOSSIER_CONTRATS = RACINE_SERVICE / "contrats"
ENVELOPPE = {"erreur", "detail", "mode"}
NOMS_ORIANE = ("platformId", "publishedAt", "onScreenText", "transcript", "profileHandle", "viewsCount")

# Routes du contrat api.v1, avec un corps valide quand la route en attend un.
ROUTES_API_V1: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/v1/etat", None),
    ("GET", "/v1/journal", None),
    ("GET", "/v1/radar", None),
    ("POST", "/v1/radar/actualiser", None),
    ("GET", "/v1/recits/r1", None),
    ("GET", "/v1/videos/v1", None),
    ("POST", "/v1/comparaisons", {"video_source": "v1", "video_reprise": "v2"}),
    ("GET", "/v1/comparaisons/c1", None),
    ("POST", "/v1/fiches", {"comparaison": "c1"}),
    ("GET", "/v1/fiches/f1", None),
    ("PATCH", "/v1/fiches/f1", {"constat": "constat écrit par le journaliste"}),
    ("POST", "/v1/fiches/f1/decision", {"valeur": "a_verifier", "role": "journaliste"}),
    ("GET", "/v1/fiches/f1/export", None),
]


def _mesure(**surcharges: Any) -> dict[str, Any]:
    donnees: dict[str, Any] = {
        "nom": "conversations observées",
        "valeur": 5,
        "unite": "vidéos",
        "methode": "nombre de vidéos rendues par Oriane sur la fenêtre de la requête",
        "fenetre": {"debut": "2026-10-31T00:00:00+00:00", "fin": "2026-11-07T00:00:00+00:00"},
        "echantillon": {"resultats_consultes": 5, "limite_page": 100, "tronque": False},
        "source": "Oriane",
    }
    donnees.update(surcharges)
    return donnees


def _fiche(**surcharges: Any) -> dict[str, Any]:
    version = {
        "video": "v1",
        "lien": "https://exemple.invalid/v1",
        "compte": "compte_simule",
        "date": LUE_LE_TEST,
    }
    donnees: dict[str, Any] = {
        "identifiant": "f1",
        "comparaison": "c1",
        "requete": "phrase simulée",
        "versions": [version, {**version, "video": "v2"}],
        "limites": [{"type": "libelle", "texte": LIMITE_TRANSCRIPTIONS}],
        "resume": {"segments": [{"type": "libelle", "texte": "Deux versions comparées au mot."}]},
        "mode": "enregistre",
        "enregistre_le": ENREGISTRE_LE_TEST,
    }
    donnees.update(surcharges)
    return donnees


def _cles(objet: Any) -> set[str]:
    """Toutes les clés de propriétés déclarées dans un schéma JSON, à toute profondeur."""
    cles: set[str] = set()
    if isinstance(objet, dict):
        for nom, valeur in objet.items():
            if nom == "properties" and isinstance(valeur, dict):
                cles.update(valeur)
            cles |= _cles(valeur)
    elif isinstance(objet, list):
        for valeur in objet:
            cles |= _cles(valeur)
    return cles


def _lire_contrat(nom: str) -> Any:
    return json.loads((DOSSIER_CONTRATS / nom).read_text(encoding="utf-8"))


# --- mots.v1 -----------------------------------------------------------------------------------


def test_mots_apostrophe_trait_d_union_ponctuation():
    assert normaliser("L'État paie-t-il ?") == ["l", "état", "paie", "t", "il"]


def test_mots_nombres_gardes_tels_que_transcrits():
    assert normaliser("dix mille") == ["dix", "mille"]
    assert normaliser("10 000") == ["10", "000"]
    assert normaliser("dix mille") != normaliser("10 000")


def test_mots_separateur_decimal_garde_entre_deux_chiffres():
    assert normaliser("3,5 milliards") == ["3,5", "milliards"]
    assert normaliser("3,5 milliards") != normaliser("35 milliards")
    assert normaliser("3.5 %") == ["3.5"]
    assert normaliser("1 000") == ["1", "000"]
    assert normaliser("Rendez-vous en 2027.") == ["rendez", "vous", "en", "2027"]
    assert normaliser("oui, 3, non.") == ["oui", "3", "non"]


def test_mots_forme_composee_et_apostrophe_typographique():
    decompose = "État"  # É en forme décomposée
    assert normaliser(decompose) == ["état"]
    assert normaliser("aujourd’hui, c’est « dit » !") == ["aujourd", "hui", "c", "est", "dit"]


# --- libellés refusés --------------------------------------------------------------------------


@pytest.mark.parametrize("texte", ["version originale", "Fausse", "premières", "Un récit MANIPULÉ"])
def test_libelles_refuses(texte):
    assert contient_libelle_refuse(texte) is not None


@pytest.mark.parametrize("texte", ["PREMIERE", "première", "déformé", "deforme", "manipule", "coordonne"])
def test_libelles_refuses_avec_ou_sans_accent(texte):
    assert contient_libelle_refuse(texte) is not None


def test_desaccentuation_ne_change_pas_mots_v1():
    assert normaliser("première") == ["première"]


def test_libelles_six_racines_et_accords():
    for racine in ("faux", "première", "originale", "manipulé", "coordonné", "déformé"):
        assert racine in LIBELLES_REFUSES
    assert len(LIBELLES_REFUSES) == 23


@pytest.mark.parametrize(
    "texte", [LIBELLE_PLUS_ANCIENNE_VERSION, "indices de transformation", "conversations observées"]
)
def test_libelles_acceptes(texte):
    assert contient_libelle_refuse(texte) is None


def test_libelles_par_mot_entier():
    assert contient_libelle_refuse("fauxbourg originalité premièrement") is None


def test_segment_libelle_refuse_citation_acceptee():
    with pytest.raises(ValidationError, match="libellé refusé"):
        Segment(type="libelle", texte="Cette vidéo est fausse")
    assert Segment(type="citation", texte="« c'est faux », dit le compte simulé").type == "citation"


def test_constat_jamais_filtre():
    fiche = Fiche.model_validate(_fiche(constat="Le chiffre cité est faux selon la source officielle."))
    assert "faux" in fiche.constat


def test_libelle_refuse_dans_un_resume_refuse():
    with pytest.raises(ValidationError):
        Fiche.model_validate(_fiche(resume={"segments": [{"type": "libelle", "texte": "Version originale"}]}))


# --- modèles -----------------------------------------------------------------------------------


def test_video_simulee_valide(video_simulee, deux_videos_comparables):
    video = video_simulee(identifiant="v2")
    assert video.transcription.source == "Oriane"
    assert video.transcription.niveau == "default"
    source, reprise = deux_videos_comparables
    assert source.identifiant != reprise.identifiant
    assert source.transcription.texte and reprise.transcription.texte


@pytest.mark.parametrize("champ", CHAMPS_TIERS_ORIANE)
def test_video_refuse_champ_de_tiers(champ):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        fabriquer_video(**{champ: "valeur fictive"})


def test_video_refuse_nom_oriane(reponse_oriane_simulee):
    brut = reponse_oriane_simulee["data"]["results"][0]
    assert "popularComments" in brut and "transcript" in brut["media"][0]
    with pytest.raises(ValidationError):
        fabriquer_video(publishedAt=brut["publishedAt"])
    with pytest.raises(ValidationError):
        fabriquer_video(transcription={"texte": "x", "lue_le": LUE_LE_TEST, "transcript": "x"})


def test_transcription_attribuee_a_oriane():
    with pytest.raises(ValidationError):
        fabriquer_video(transcription={"texte": "x", "source": "Whisper", "lue_le": LUE_LE_TEST})


def test_mode_enregistre_exige_enregistre_le():
    with pytest.raises(ValidationError, match="enregistre_le"):
        fabriquer_video(enregistre_le=None)
    with pytest.raises(ValidationError, match="enregistre_le"):
        fabriquer_video(mode="direct")
    assert fabriquer_video(mode="direct", enregistre_le=None).mode == "direct"
    with pytest.raises(ValidationError):
        fabriquer_video(mode="simule")


def test_mesure_sans_methode_ni_fenetre_refusee():
    assert Mesure.model_validate(_mesure()).methode
    for absent in ("methode", "fenetre"):
        donnees = _mesure()
        del donnees[absent]
        with pytest.raises(ValidationError):
            Mesure.model_validate(donnees)
    with pytest.raises(ValidationError):
        Mesure.model_validate(_mesure(methode=""))


def test_mesure_nulle_dit_sa_raison():
    with pytest.raises(ValidationError, match="raison"):
        Mesure.model_validate(_mesure(valeur=None))
    assert Mesure.model_validate(_mesure(valeur=None, raison="échantillon trop petit")).valeur is None


def test_recit_porte_le_libelle_fixe():
    recit = Recit.model_validate(
        {
            "identifiant": "r1",
            "phrase_surveillee": "c'est faux",
            "requete_en_clair": "transcript contient « c'est faux »",
            "mesures": [_mesure()],
            "plus_ancienne_version": {"video": "v1", "publie_le": LUE_LE_TEST},
            "calcule_le": LUE_LE_TEST,
            "mode": "enregistre",
            "enregistre_le": ENREGISTRE_LE_TEST,
        }
    )
    assert recit.plus_ancienne_version.libelle == LIBELLE_PLUS_ANCIENNE_VERSION
    with pytest.raises(ValidationError):
        Recit.model_validate(
            {
                **recit.model_dump(mode="json"),
                "plus_ancienne_version": {
                    "video": "v1",
                    "publie_le": LUE_LE_TEST,
                    "libelle": "première version",
                },
            }
        )


def test_decision_hors_des_trois_refusee():
    for valeur in ("a_verifier", "ne_pas_amplifier", "pret_a_traiter"):
        assert Decision(valeur=valeur, role="journaliste", heure=LUE_LE_TEST).valeur == valeur
    with pytest.raises(ValidationError):
        Decision(valeur="faux", role="journaliste", heure=LUE_LE_TEST)


def test_ecart_sans_qualification():
    ecart = Ecart.model_validate(
        {
            "identifiant": "c1",
            "video_source": "v1",
            "video_reprise": "v2",
            "operations": [
                {"type": "retire", "position_source": 5, "position_reprise": 5, "mots_source": ["si"]}
            ],
            "transcriptions": {"source": {"lue_le": LUE_LE_TEST}, "reprise": {"lue_le": LUE_LE_TEST}},
            "mode": "enregistre",
            "enregistre_le": ENREGISTRE_LE_TEST,
        }
    )
    assert ecart.normalisation == "mots.v1"
    assert ecart.heure_dans_la_video.secondes is None
    assert ecart.heure_dans_la_video.libelle == "non fournie au niveau default"
    assert ecart.transcriptions.reprise.source == "Oriane"
    with pytest.raises(ValidationError):
        Ecart.model_validate({**ecart.model_dump(mode="json"), "score": 0.4})
    proprietes = _cles(schema_contrat("ecart.v1"))
    assert not proprietes & {"score", "verdict", "qualification", "fiabilite"}


def test_operation_coherente():
    with pytest.raises(ValidationError):
        Operation(type="ajoute", position_source=0, position_reprise=0, mots_source=["x"])
    with pytest.raises(ValidationError):
        Operation(type="remplace", position_source=0, position_reprise=0, mots_source=["x"])


def test_fiche_deux_versions_et_limite_transcriptions():
    fiche = Fiche.model_validate(_fiche())
    assert fiche.constat == "" and fiche.decision is None
    assert {v.etat for v in fiche.versions} == {"a_trancher"}
    assert fiche.resume.methode == "gabarit v1"
    with pytest.raises(ValidationError):
        Fiche.model_validate(_fiche(versions=_fiche()["versions"][:1]))
    with pytest.raises(ValidationError, match="limites"):
        Fiche.model_validate(_fiche(limites=[]))


def test_comparaison_de_deux_videos_distinctes():
    with pytest.raises(ValidationError):
        DemandeComparaison(video_source="v1", video_reprise="v1")


# --- schémas exportés et OpenAPI ---------------------------------------------------------------


@pytest.mark.parametrize("nom", sorted(CONTRATS))
def test_schema_egal_a_son_fichier(nom):
    assert _lire_contrat(f"{nom}.schema.json") == json.loads(json.dumps(schema_contrat(nom)))


@pytest.mark.parametrize("nom", sorted(CONTRATS))
def test_aucun_nom_oriane_dans_les_schemas(nom):
    schema = schema_contrat(nom)
    assert not _cles(schema) & set(NOMS_ORIANE)
    texte = json.dumps(schema)
    for nom_oriane in ("platformId", "publishedAt", "onScreenText", '"transcript"'):
        assert nom_oriane not in texte


def test_openapi_egal_au_contrat(config_test):
    application = creer_application(config_test)
    assert _lire_contrat("api.v1.json") == json.loads(json.dumps(application.openapi()))


def test_openapi_titre_version_et_erreur(config_test):
    schema = creer_application(config_test).openapi()
    assert schema["info"] == {"title": "Tête de Brut. — service de démonstration", "version": "api.v1"}
    assert set(schema["components"]["schemas"]["Erreur"]["properties"]) == ENVELOPPE
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    for chemin, operations in schema["paths"].items():
        assert chemin.startswith("/v1/"), chemin
        for methode, operation in operations.items():
            assert operation["summary"], (methode, chemin)
            assert "501" in operation["responses"], (methode, chemin)
            for statut, reponse in operation["responses"].items():
                if statut.startswith(("4", "5")):
                    assert reponse["content"]["application/json"]["schema"] == {
                        "$ref": "#/components/schemas/Erreur"
                    }, (methode, chemin, statut)
    assert "text/html" in schema["paths"]["/v1/fiches/{id}/export"]["get"]["responses"]["200"]["content"]


def test_exporteur_verifie_les_contrats():
    spec = importlib.util.spec_from_file_location(
        "exporter_contrats", RACINE_SERVICE / "scripts/exporter_contrats.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--verifier"]) == 0
    assert set(module.contrats_attendus()) == {p.name for p in DOSSIER_CONTRATS.glob("*.json")}


# --- routes ------------------------------------------------------------------------------------


def test_routes_toutes_sous_v1_sauf_sante(client):
    documentees = {(m.upper(), c) for c, ops in client.app.openapi()["paths"].items() for m in ops}
    attendues = {(m, c) for m, c, _ in ROUTES_API_V1}
    assert len(documentees) == len(attendues) == 13
    hors_documentation = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/sante"}
    assert routeur_v1.prefix == "/v1"
    for route in client.app.routes:
        chemin = getattr(route, "path", None)
        if chemin is None:  # routeur inclus (FastAPI le garde tel quel) : seul `/v1` est permis
            assert getattr(route, "original_router", None) is routeur_v1
        else:
            assert chemin in hors_documentation, chemin
    assert "/sante" not in client.app.openapi()["paths"]


# Routes remplies par un mandat : elles quittent la liste des 501 et ont leurs propres tests
# (S03 : vidéos ; S05 : radar et récits ; S07 : comparaisons ; S08 : fiches ; S04 : état, journal).
ROUTES_IMPLEMENTEES = {
    ("GET", "/v1/videos/v1"),
    ("GET", "/v1/radar"),
    ("GET", "/v1/recits/r1"),
    ("POST", "/v1/comparaisons"),
    ("GET", "/v1/comparaisons/c1"),
    ("POST", "/v1/fiches"),
    ("GET", "/v1/fiches/f1"),
    ("PATCH", "/v1/fiches/f1"),
    ("POST", "/v1/fiches/f1/decision"),
    ("GET", "/v1/fiches/f1/export"),
    ("GET", "/v1/etat"),  # S04
    ("GET", "/v1/journal"),
    ("POST", "/v1/radar/actualiser"),
}


@pytest.mark.parametrize(
    ("methode", "chemin", "corps"),
    [r for r in ROUTES_API_V1 if (r[0], r[1]) not in ROUTES_IMPLEMENTEES],
)
def test_route_repond_501_dans_l_enveloppe(client, methode, chemin, corps):
    reponse = client.request(methode, chemin, json=corps)
    assert reponse.status_code == 501
    assert set(reponse.json()) == ENVELOPPE
    assert reponse.json()["erreur"] == "non_implemente"
    assert reponse.json()["mode"] in {"direct", "enregistre"}


def test_corps_invalide_rend_422_dans_l_enveloppe(client):
    reponse = client.post("/v1/fiches/f1/decision", json={"valeur": "faux", "role": "journaliste"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"] == "validation"
    assert set(reponse.json()) == ENVELOPPE
