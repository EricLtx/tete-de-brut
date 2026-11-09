"""Kit des écrans Lovable (S11, S14) : exemples de réponses validés par le contrat, textes du kit filtrés.

Les exemples de `03_Ecrans/exemples/` servent de données d'essai aux écrans tant qu'une route
répond 501. Chaque exemple doit être exactement ce que le service sérialiserait : il est validé
par le modèle pydantic de sa route, puis re-sérialisé à l'identique.

Règle des textes du kit (`README.md`, `AGENTS.md`, `prompts/*.md`) : un mot refusé n'y est admis
qu'entre accents graves (code en ligne), c'est-à-dire quand il est cité comme mot interdit ou
comme valeur ; tout le reste, textes fixes entre guillemets compris, est contrôlé.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.ecart import comparer_textes, identifiant_comparaison
from app.libelles import contient_libelle_refuse, desaccentuer
from app.modeles import (
    LIMITE_TRANSCRIPTIONS,
    ClassementPertinence,
    Ecart,
    Erreur,
    Etat,
    Fiche,
    Journal,
    Modele,
    Radar,
    Recherche,
    Recit,
    ResultatRecherche,
    SuppressionRecit,
    Video,
)
from app.mots import normaliser

RACINE_DEPOT = Path(__file__).resolve().parents[2]
DOSSIER_KIT = RACINE_DEPOT / "03_Ecrans"
DOSSIER_EXEMPLES = DOSSIER_KIT / "exemples"
CONTRAT_API = RACINE_DEPOT / "02_Service" / "contrats" / "api.v1.json"
LIMITE_INSTRUCTIONS = 10_000  # octets, comme `wc -c` : plus strict que la limite en caractères

# Préfixe du nom de fichier -> modèle de la route.
MODELES_PAR_PREFIXE: dict[str, type[Modele]] = {
    "etat": Etat,
    "radar": Radar,
    "recit": Recit,
    "suppression": SuppressionRecit,
    "pertinence": ClassementPertinence,
    "video": Video,
    "comparaison": Ecart,
    "fiche": Fiche,
    "journal": Journal,
    "erreur": Erreur,
}
# Exemples de la recherche (S14) : le préfixe `recherche` ne suffit pas, la réponse dépend du fichier.
MODELES_PAR_NOM: dict[str, type[Modele]] = {
    "recherche-preparee": Recherche,
    "recherche-refus": Recherche,
    "recherche-executee": ResultatRecherche,
}
PROMPTS_ATTENDUS = {
    "00-projet.md",
    "01-radar.md",
    "02-versions.md",
    "03-fiche.md",
    "04-recherche.md",
}
NOMS_ORIANE = ("platformId", "publishedAt", "onScreenText", "transcript", "profileHandle", "viewsCount")
MOTS_INTERDITS_KIT = frozenset(
    {"tendance", "tendances", "viral", "virale", "viraux", "virales", "sentiment", "sentiments"}
)
ENREGISTRE_LE = "2026-11-07T08:00:00Z"

FICHIERS_EXEMPLES = sorted(DOSSIER_EXEMPLES.glob("*.json"))
TEXTES_KIT = [
    DOSSIER_KIT / "README.md",
    DOSSIER_KIT / "AGENTS.md",
    *sorted((DOSSIER_KIT / "prompts").glob("*.md")),
]


def _lire(nom: str) -> Any:
    return json.loads((DOSSIER_EXEMPLES / nom).read_text(encoding="utf-8"))


def _modele_de(chemin: Path) -> type[Modele]:
    return MODELES_PAR_NOM.get(chemin.stem) or MODELES_PAR_PREFIXE[chemin.stem.split("-")[0]]


def _parcourir(valeur: Any):
    """Rend chaque objet JSON (dictionnaire) de l'arbre, en profondeur."""
    if isinstance(valeur, dict):
        yield valeur
        for sous in valeur.values():
            yield from _parcourir(sous)
    elif isinstance(valeur, list):
        for sous in valeur:
            yield from _parcourir(sous)


def test_le_kit_est_complet() -> None:
    attendus = {
        "etat.json",
        "radar.json",
        "recit.json",
        "video-source.json",
        "video-reprise.json",
        "comparaison.json",
        "fiche-avant-decision.json",
        "fiche-apres-decision.json",
        "journal.json",
        "erreur-401-cle-demo.json",
        "erreur-409-decision-manquante.json",
        "recherche-preparee.json",
        "recherche-executee.json",
        "recherche-refus.json",
    }
    assert attendus <= {f.name for f in FICHIERS_EXEMPLES}
    for chemin in TEXTES_KIT:
        assert chemin.is_file(), chemin
    assert {p.name for p in (DOSSIER_KIT / "prompts").glob("*.md")} == PROMPTS_ATTENDUS


def test_chaque_reponse_du_contrat_a_son_exemple() -> None:
    contrat = json.loads(CONTRAT_API.read_text(encoding="utf-8"))
    modeles_exemples = {_modele_de(f).__name__ for f in FICHIERS_EXEMPLES}
    for chemin, operations in contrat["paths"].items():
        for methode, operation in operations.items():
            for statut, reponse in operation["responses"].items():
                schema = reponse.get("content", {}).get("application/json", {}).get("schema", {})
                ref = schema.get("$ref", "")
                if statut.startswith("2") and ref:
                    nom = ref.rsplit("/", 1)[-1]
                    assert nom in modeles_exemples, f"{methode.upper()} {chemin} : aucun exemple {nom}"


@pytest.mark.parametrize("chemin", FICHIERS_EXEMPLES, ids=lambda p: p.name)
def test_exemple_valide_par_le_modele_de_sa_route(chemin: Path) -> None:
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    modele = _modele_de(chemin).model_validate(donnees)
    assert modele.model_dump(mode="json") == donnees, "l'exemple diffère de ce que le service sérialise"


@pytest.mark.parametrize("chemin", FICHIERS_EXEMPLES, ids=lambda p: p.name)
def test_exemple_en_mode_enregistre(chemin: Path) -> None:
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["mode"] == "enregistre"
    if _modele_de(chemin) is not Erreur:  # l'enveloppe d'erreur ne porte que `mode`
        assert donnees["enregistre_le"] == ENREGISTRE_LE
    for objet in _parcourir(donnees):
        if "mode" in objet and "enregistre_le" in objet and objet["mode"] == "enregistre":
            assert objet["enregistre_le"] == ENREGISTRE_LE


@pytest.mark.parametrize("chemin", FICHIERS_EXEMPLES, ids=lambda p: p.name)
def test_exemple_sans_libelle_refuse_ni_nom_oriane(chemin: Path) -> None:
    texte = chemin.read_text(encoding="utf-8")
    donnees = json.loads(texte)
    for objet in _parcourir(donnees):
        if objet.get("type") == "libelle":
            assert contient_libelle_refuse(objet["texte"]) is None, objet["texte"]
        for cle in objet:
            assert cle not in NOMS_ORIANE, cle
        if "echantillon" in objet:  # une mesure : jamais sans méthode ni fenêtre
            assert objet["methode"].strip() and objet["fenetre"]
    for nom in NOMS_ORIANE:
        assert not re.search(rf"\b{nom}\b", texte), f"nom de champ Oriane dans {chemin.name} : {nom}"


@pytest.mark.parametrize("chemin", FICHIERS_EXEMPLES, ids=lambda p: p.name)
def test_exemple_fictif(chemin: Path) -> None:
    """Comptes et liens des exemples sont marqués « fictif » : aucune personne ni compte réel."""
    for objet in _parcourir(json.loads(chemin.read_text(encoding="utf-8"))):
        for cle in ("compte", "lien"):
            if cle in objet:
                assert "fictif" in objet[cle].lower(), f"{cle} non marqué fictif : {objet[cle]}"


def test_exemples_coherents_entre_eux() -> None:
    radar, recit = _lire("radar.json"), _lire("recit.json")
    source, reprise = _lire("video-source.json"), _lire("video-reprise.json")
    comparaison = _lire("comparaison.json")
    avant, apres = _lire("fiche-avant-decision.json"), _lire("fiche-apres-decision.json")
    ids_videos = {source["identifiant"], reprise["identifiant"]}

    assert radar["recits"][0] == recit
    assert any(not r["videos"] for r in radar["recits"]), "un récit vide montre l'état vide"
    assert set(recit["videos"]) == ids_videos
    assert recit["plus_ancienne_version"]["video"] == source["identifiant"]

    assert comparaison["video_source"] == source["identifiant"]
    assert comparaison["video_reprise"] == reprise["identifiant"]
    assert comparaison["identifiant"] == identifiant_comparaison(
        source["identifiant"], reprise["identifiant"]
    )
    for champ, cle in (
        ("operations", None),
        ("ecart_legende", "legende"),
        ("ecart_texte_ecran", "texte_ecran"),
    ):
        texte_s = source["transcription"]["texte"] if cle is None else source[cle]
        texte_r = reprise["transcription"]["texte"] if cle is None else reprise[cle]
        if isinstance(texte_s, dict):
            texte_s, texte_r = texte_s["texte"], texte_r["texte"]
        attendu = [o.model_dump(mode="json") for o in comparer_textes(texte_s, texte_r)]
        assert comparaison[champ] == attendu, champ
    types = {o["type"] for o in comparaison["operations"]}
    assert {"retire", "remplace"} <= types, "l'écart au mot doit être visible : mots retirés et un remplacé"

    for fiche in (avant, apres):
        assert fiche["comparaison"] == comparaison["identifiant"]
        assert {v["video"] for v in fiche["versions"]} == ids_videos
        assert any(s["texte"] == LIMITE_TRANSCRIPTIONS for s in fiche["limites"])
    assert avant["constat"] == "" and avant["decision"] is None
    assert {v["etat"] for v in avant["versions"]} == {"a_trancher"}
    assert apres["constat"].strip() and apres["decision"] is not None
    assert "a_trancher" not in {v["etat"] for v in apres["versions"]}

    assert _lire("erreur-409-decision-manquante.json")["erreur"] == "decision_manquante"
    assert _lire("erreur-401-cle-demo.json")["erreur"] == "cle_demo_invalide"


def test_exemples_de_la_recherche() -> None:
    preparee, refus = _lire("recherche-preparee.json"), _lire("recherche-refus.json")
    executee = _lire("recherche-executee.json")
    radar = _lire("radar.json")

    assert preparee["refus"] is None and preparee["type"] == "phrase"
    filtres = preparee["filtres"]
    assert filtres["phrases"] and set(filtres["noyaux"]) < set(filtres["phrases"]), "noyaux + phrases"
    assert filtres["fenetre"] and filtres["plateformes"] and filtres["comptes_exclus"]
    assert preparee["reformulation"] == "modele"
    assert preparee["requete_en_clair"].startswith("reformulée par un modèle de langue")
    assert all(p in preparee["requete_en_clair"] for p in filtres["phrases"]), "les filtres affichés partent"
    assert preparee["cout_estime"]["credits_estimes"] > 0

    assert refus["refus"]["code"] == "nom_seul" and refus["refus"]["detail"].strip()
    assert refus["cout_estime"]["credits_estimes"] == 0, "une recherche refusée ne coûte rien"
    assert "rien n'est envoyé" in refus["requete_en_clair"]

    assert executee["recherche"] == preparee, "le lancement rend la recherche préparée"
    assert executee["video"] is None, "type phrase : un récit, pas de vidéo"
    recit = executee["recit"]
    assert recit in radar["recits"], "le récit lancé est déjà au radar"
    assert recit["phrase_surveillee"] in preparee["filtres"]["phrases"]
    assert recit.get("variantes") in (None, filtres["phrases"])


def test_le_kit_cite_toutes_les_routes_du_contrat() -> None:
    """`AGENTS.md` liste chaque route de `api.v1` : une route absente est une route que l'écran ignore."""
    contrat = json.loads(CONTRAT_API.read_text(encoding="utf-8"))
    instructions = (DOSSIER_KIT / "AGENTS.md").read_text(encoding="utf-8")
    absentes = [
        f"{methode.upper()} {chemin}"
        for chemin, operations in contrat["paths"].items()
        for methode in operations
        if f"`{methode.upper()} {chemin}" not in instructions
    ]
    assert not absentes, f"AGENTS.md ne cite pas : {absentes}"
    for route in ("DELETE /v1/recits/{id}", "/v1/recits/{id}/pertinence", "/v1/recherches/preparer"):
        assert route in instructions
    assert "recit.variantes" in instructions
    assert "recit.variantes" in (DOSSIER_KIT / "README.md").read_text(encoding="utf-8")


def test_le_kit_compte_quatre_ecrans() -> None:
    instructions = (DOSSIER_KIT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Exactement quatre écrans" in instructions
    for route in ("`/` Recherche", "`/radar` Radar", "`/versions/:id`", "`/fiche/:id`"):
        assert route in instructions, route
    assert "trois écrans" not in instructions.lower()
    radar = (DOSSIER_KIT / "prompts" / "01-radar.md").read_text(encoding="utf-8")
    recherche = (DOSSIER_KIT / "prompts" / "04-recherche.md").read_text(encoding="utf-8")
    assert "sur la route `/radar`" in radar
    assert "sur la route `/`" in recherche


@pytest.mark.parametrize("chemin", TEXTES_KIT, ids=lambda p: p.name)
def test_exemples_cites_par_le_kit_existent(chemin: Path) -> None:
    cites = set(re.findall(r"exemples/([\w.-]+\.json)", chemin.read_text(encoding="utf-8")))
    presents = {f.name for f in FICHIERS_EXEMPLES}
    assert cites <= presents, f"{chemin.name} cite des exemples absents : {sorted(cites - presents)}"


def _hors_code(texte: str) -> str:
    """Le texte sans ses spans de code en ligne (seul endroit où un mot refusé est admis)."""
    return re.sub(r"`[^`\n]*`", " ", texte)


@pytest.mark.parametrize("chemin", TEXTES_KIT, ids=lambda p: p.name)
def test_textes_du_kit_sans_mot_refuse(chemin: Path) -> None:
    for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1):
        visible = _hors_code(ligne)
        mot = contient_libelle_refuse(visible)
        assert mot is None, f"{chemin.name}:{numero} : libellé refusé « {mot} » hors code"
        interdits = {desaccentuer(m) for m in normaliser(visible)} & MOTS_INTERDITS_KIT
        assert not interdits, f"{chemin.name}:{numero} : mot interdit {sorted(interdits)} hors code"


def test_instructions_lovable_sous_la_limite() -> None:
    taille = len((DOSSIER_KIT / "AGENTS.md").read_bytes())
    assert taille <= LIMITE_INSTRUCTIONS, f"AGENTS.md : {taille} octets > {LIMITE_INSTRUCTIONS}"


# Chemin JSON cité entre accents graves : `recits[].mesures[].methode`, `transcription.lue_le`, `videos[]`.
CHEMIN_JSON = re.compile(r"`([a-z_]+(?:\[\])?(?:\.[a-z_]+(?:\[\])?)*)`")


def _sous_schemas(schema: dict[str, Any], schemas: dict[str, Any]) -> list[dict[str, Any]]:
    """Schémas atteignables sans propriété : référence, union, élément de liste."""
    if "$ref" in schema:
        return _sous_schemas(schemas[schema["$ref"].rsplit("/", 1)[-1]], schemas)
    trouves = [schema]
    for cle in ("anyOf", "oneOf", "allOf"):
        for sous in schema.get(cle, []):
            trouves += _sous_schemas(sous, schemas)
    if "items" in schema:
        trouves += _sous_schemas(schema["items"], schemas)
    return trouves


def _chemin_existe(chemin: str, schemas: dict[str, Any]) -> bool:
    segments = [s.removesuffix("[]") for s in chemin.split(".")]
    for depart in schemas.values():
        courants = _sous_schemas(depart, schemas)
        for segment in segments:
            suivants = []
            for schema in courants:
                propriete = schema.get("properties", {}).get(segment)
                if propriete is not None:
                    suivants += _sous_schemas(propriete, schemas)
            courants = suivants
            if not courants:
                break
        if courants:
            return True
    return False


@pytest.mark.parametrize("chemin", TEXTES_KIT, ids=lambda p: p.name)
def test_chemins_json_cites_existent_au_contrat(chemin: Path) -> None:
    schemas = json.loads(CONTRAT_API.read_text(encoding="utf-8"))["components"]["schemas"]
    cites = {m for m in CHEMIN_JSON.findall(chemin.read_text(encoding="utf-8")) if "." in m or "[]" in m}
    absents = sorted(c for c in cites if not _chemin_existe(c, schemas))
    assert not absents, f"{chemin.name} : chemins absents du contrat api.v1 : {absents}"
