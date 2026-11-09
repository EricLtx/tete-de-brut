"""Rejoue un jeu d'or `jeu.v1` contre un bras de recherche et écrit un rapport en comptes (S22).

    python scripts/evaluer.py --jeu evaluation/donnees/jeu-or.json --bras unique --adresse http://localhost:8080

Bras `unique` : `POST /v1/recherches` du service tel qu'il est. Les bras `multi` et `boucle` sont
déclarés mais refusés (« disponible à partir de S29 »). Pour chaque question : rappel@k, nDCG@k,
faits couverts (lus dans les vidéos rendues), crédits, jetons, latence. Le rapport donne des comptes
(« 4 questions sur 6 ») et se présente comme un contrôle de cohérence, jamais comme une inférence
statistique. Il est écrit dans `--sortie` (par défaut `evaluation/donnees/`, ignoré par Git) et imprimé.

Si `CLE_DEMO` est dans l'environnement, elle est envoyée dans `X-Cle-Demo`.
Le rapport nomme les questions par leur identifiant, jamais par leur texte ni par un compte.
Code de sortie : 0 rapport écrit ; 1 service injoignable ; 2 jeu mal formé, bras indisponible ou usage.
Bibliothèque standard et `httpx` ; le script n'importe rien du service, seulement `evaluation/`.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from evaluation.metriques import (  # noqa: E402
    K_PAR_DEFAUT,
    Jeu,
    JeuInvalide,
    QuestionDuJeu,
    faits_couverts,
    ndcg_a_k,
    pertinentes_retrouvees,
    rappel_a_k,
    valider_jeu,
)

EN_TETE_CLE_DEMO = "X-Cle-Demo"
DELAI_S = 60.0
BRAS = ("unique", "multi", "boucle")
BRAS_DISPONIBLES = ("unique",)
MESSAGE_BRAS = (
    "bras « {bras} » : disponible à partir de S29 (seul le bras « unique » se rejoue pour l'instant)"
)
DOSSIER_DONNEES = RACINE / "evaluation" / "donnees"
LECTURE = (
    "Lecture : contrôle de cohérence sur {n} question(s), pas une inférence statistique ; "
    "ces comptes ne se généralisent pas au-delà du jeu."
)
JETONS_NON_MESURES = "non mesurés (le bras unique n'appelle aucun modèle ; mesurés dès S27)"


class BrasIndisponible(Exception):
    """Le bras demandé est déclaré mais pas encore branché."""


@dataclass
class ResultatQuestion:
    """Ce que le bras a rendu pour une question, et les mesures qui en découlent."""

    identifiant: str
    rendues: list[str] = field(default_factory=list)
    pertinentes_attendues: int = 0
    pertinentes_retrouvees: int = 0
    rappel: float = 0.0
    ndcg: float = 0.0
    faits_attendus: int = 0
    faits_couverts: int = 0
    credits: int = 0
    jetons: int | None = None
    latence_s: float = 0.0
    mode: str = ""
    echec: str = ""  # vide si le service a répondu 201 ; sinon code d'erreur ou raison, sans détail de tiers


def charger_jeu(chemin: Path) -> Jeu:
    """Lit et valide un jeu `jeu.v1` ; lève `JeuInvalide` (fichier illisible compris)."""
    try:
        document = json.loads(chemin.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JeuInvalide(f"jeu illisible ({type(exc).__name__})") from exc
    except ValueError as exc:
        raise JeuInvalide("jeu : JSON mal formé") from exc
    return valider_jeu(document)


def _textes_video(client: httpx.Client, identifiant: str, entetes: dict[str, str]) -> list[str]:
    """Légende, transcription et texte à l'écran d'une vidéo ; vide si le service ne la sert pas."""
    reponse = client.get(f"/v1/videos/{identifiant}", headers=entetes)
    if reponse.status_code != 200:
        return []
    video = reponse.json()
    return [
        video.get("legende", ""),
        video.get("transcription", {}).get("texte", ""),
        video.get("texte_ecran", {}).get("texte", ""),
    ]


def evaluer_unique(
    client: httpx.Client, question: QuestionDuJeu, k: int, entetes: dict[str, str] | None = None
) -> ResultatQuestion:
    """Bras `unique` : une requête `POST /v1/recherches`, mesurée sur les `k` premières vidéos rendues."""
    entetes = entetes or {}
    resultat = ResultatQuestion(
        identifiant=question.identifiant,
        pertinentes_attendues=len(question.videos_pertinentes),
        faits_attendus=len(question.faits_attendus),
    )
    debut = time.perf_counter()
    reponse = client.post("/v1/recherches", json={"question": question.question}, headers=entetes)
    resultat.latence_s = time.perf_counter() - debut
    if reponse.status_code != 201:
        try:
            resultat.echec = f"{reponse.status_code} {reponse.json()['erreur']}"
        except (ValueError, KeyError, TypeError):
            resultat.echec = str(reponse.status_code)
        return resultat
    corps = reponse.json()
    recit, video = corps.get("recit"), corps.get("video")
    resultat.rendues = list(recit["videos"]) if recit else ([video["identifiant"]] if video else [])
    resultat.mode = corps.get("mode", "")
    # En mode enregistré, rien n'est envoyé à Oriane : aucun crédit dépensé.
    if resultat.mode == "direct":
        resultat.credits = corps["recherche"]["cout_estime"]["credits_estimes"]
    resultat.pertinentes_retrouvees = pertinentes_retrouvees(resultat.rendues, question.videos_pertinentes, k)
    resultat.rappel = rappel_a_k(resultat.rendues, question.videos_pertinentes, k)
    resultat.ndcg = ndcg_a_k(resultat.rendues, question.videos_pertinentes, k)
    textes: list[str] = []
    for identifiant in resultat.rendues[:k]:
        textes.extend(_textes_video(client, identifiant, entetes))
    resultat.faits_couverts = faits_couverts(question.faits_attendus, textes)
    return resultat


def evaluer(client: httpx.Client, jeu: Jeu, bras: str, k: int, cle: str = "") -> list[ResultatQuestion]:
    """Rejoue chaque question du jeu sur le bras demandé ; `BrasIndisponible` avant tout appel."""
    if bras not in BRAS_DISPONIBLES:
        raise BrasIndisponible(MESSAGE_BRAS.format(bras=bras))
    entetes = {EN_TETE_CLE_DEMO: cle} if cle else {}
    return [evaluer_unique(client, question, k, entetes) for question in jeu.questions]


# --- rapport --------------------------------------------------------------------------------------


def _s(valeur: float) -> str:
    return f"{valeur:.2f} s"


def rapport_texte(jeu: Jeu, bras: str, k: int, resultats: list[ResultatQuestion]) -> str:
    """Rapport lisible en comptes : une ligne par question, puis la synthèse du jeu."""
    n = len(resultats)
    lignes = [
        f"Banc d'évaluation, bras {bras} : jeu « {jeu.nom} », {n} question(s), k = {k}",
        "",
    ]
    for r in resultats:
        if r.echec:
            lignes.append(
                f"- {r.identifiant} : sans réponse du service ({r.echec}), latence {_s(r.latence_s)}"
            )
            continue
        lignes.append(
            f"- {r.identifiant} : rappel@{k} {r.pertinentes_retrouvees}/{r.pertinentes_attendues}, "
            f"nDCG@{k} {r.ndcg:.2f}, faits {r.faits_couverts}/{r.faits_attendus}, "
            f"crédits {r.credits}, latence {_s(r.latence_s)}, mode {r.mode}"
        )
    repondues = [r for r in resultats if not r.echec]
    toutes_retrouvees = sum(1 for r in repondues if r.pertinentes_retrouvees == r.pertinentes_attendues)
    au_moins_une = sum(1 for r in repondues if r.pertinentes_retrouvees > 0)
    tous_les_faits = sum(1 for r in repondues if r.faits_couverts == r.faits_attendus)
    total_attendues = sum(r.pertinentes_attendues for r in resultats)
    total_retrouvees = sum(r.pertinentes_retrouvees for r in resultats)
    total_faits = sum(r.faits_attendus for r in resultats)
    total_couverts = sum(r.faits_couverts for r in resultats)
    credits = sum(r.credits for r in resultats)
    latences = [r.latence_s for r in resultats]
    lignes += [
        "",
        "Synthèse en comptes",
        f"- questions répondues par le service : {len(repondues)} sur {n}",
        f"- questions dont toutes les vidéos pertinentes sont dans les {k} premières : "
        f"{toutes_retrouvees} sur {n}",
        f"- questions avec au moins une vidéo pertinente dans les {k} premières : {au_moins_une} sur {n}",
        f"- vidéos pertinentes retrouvées : {total_retrouvees} sur {total_attendues}",
        f"- questions dont tous les faits attendus sont couverts : {tous_les_faits} sur {n}",
        f"- faits couverts : {total_couverts} sur {total_faits}",
        f"- nDCG@{k} moyen sur les questions répondues : "
        + (f"{statistics.fmean(r.ndcg for r in repondues):.2f}" if repondues else "sans objet"),
        f"- crédits dépensés : {credits} (référence du jeu : {jeu.budget_credits_reference})",
        f"- jetons : {JETONS_NON_MESURES}",
        f"- latence : médiane {_s(statistics.median(latences))}, maximale {_s(max(latences))}",
        "",
        LECTURE.format(n=n),
        "",
    ]
    return "\n".join(lignes)


def rapport_json(jeu: Jeu, bras: str, k: int, resultats: list[ResultatQuestion]) -> dict[str, Any]:
    """Même contenu que le rapport lisible, pour comparer deux bras (identifiants, jamais de texte)."""
    return {
        "jeu": jeu.nom,
        "bras": bras,
        "k": k,
        "budget_credits_reference": jeu.budget_credits_reference,
        "questions": [asdict(r) for r in resultats],
    }


def ecrire_rapports(dossier: Path, jeu: Jeu, bras: str, k: int, resultats: list[ResultatQuestion]) -> Path:
    """Écrit le rapport lisible et sa version JSON dans `dossier` ; rend le chemin du rapport lisible."""
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    chemin = dossier / f"rapport-{bras}-{horodatage}.txt"
    chemin.write_text(rapport_texte(jeu, bras, k, resultats), encoding="utf-8")
    chemin.with_suffix(".json").write_text(
        json.dumps(rapport_json(jeu, bras, k, resultats), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    analyseur = argparse.ArgumentParser(description="Rejoue un jeu d'or jeu.v1 contre un bras de recherche.")
    analyseur.add_argument("--jeu", required=True, type=Path, help="fichier du jeu d'or (jeu.v1)")
    analyseur.add_argument(
        "--bras", required=True, choices=BRAS, help="bras à rejouer (unique seul pour l'instant)"
    )
    analyseur.add_argument("--adresse", default="http://localhost:8080", help="adresse du service")
    analyseur.add_argument("--k", type=int, default=K_PAR_DEFAUT, help="profondeur des mesures (défaut 10)")
    analyseur.add_argument("--sortie", type=Path, default=DOSSIER_DONNEES, help="dossier des rapports")
    arguments = analyseur.parse_args(argv)
    for flux in (sys.stdout, sys.stderr):
        flux.reconfigure(encoding="utf-8")
    if arguments.k < 1:
        print("--k doit valoir au moins 1", file=sys.stderr)
        return 2
    try:
        jeu = charger_jeu(arguments.jeu)
    except JeuInvalide as exc:
        print(f"jeu refusé : {exc}", file=sys.stderr)
        return 2
    cle = os.environ.get("CLE_DEMO", "").strip()
    proprietaire = client is None
    if client is None:
        client = httpx.Client(base_url=arguments.adresse.rstrip("/"), timeout=DELAI_S)
    try:
        resultats = evaluer(client, jeu, arguments.bras, arguments.k, cle)
    except BrasIndisponible as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except httpx.HTTPError as exc:
        print(f"service injoignable ({type(exc).__name__})", file=sys.stderr)
        return 1
    finally:
        if proprietaire:
            client.close()
    print(rapport_texte(jeu, arguments.bras, arguments.k, resultats))
    chemin = ecrire_rapports(arguments.sortie, jeu, arguments.bras, arguments.k, resultats)
    print(f"rapport écrit : {chemin.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
