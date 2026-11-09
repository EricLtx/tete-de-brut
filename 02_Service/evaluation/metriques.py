"""Métriques du banc d'évaluation : rappel@k, nDCG@k, faits couverts, validation du jeu `jeu.v1`.

Pas de dépendance : ce module ne lit ni le réseau ni le service, il calcule sur des listes.
Pertinence binaire : une vidéo est pertinente (gain 1) si la rédaction l'a trouvée à la main pour la
question, sinon non (gain 0). Le rang est l'ordre dans lequel le service rend les vidéos.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

VERSION_JEU = "jeu.v1"
K_PAR_DEFAUT = 10
FAITS_MIN, FAITS_MAX = 1, 3
QUESTION_MAX = 1000  # même borne que `DemandeRecherche.question`

CLES_JEU = {"version", "nom", "budget_credits_reference", "questions"}
CLES_QUESTION = {"id", "question", "faits_attendus", "videos_pertinentes"}


class JeuInvalide(ValueError):
    """Le jeu n'a pas la forme `jeu.v1` : le message dit où et pourquoi, en une phrase."""


@dataclass(frozen=True)
class QuestionDuJeu:
    """Une question du jeu d'or, avec ce que la rédaction en attend."""

    identifiant: str
    question: str
    faits_attendus: tuple[str, ...]
    videos_pertinentes: tuple[str, ...]


@dataclass(frozen=True)
class Jeu:
    """Jeu d'or `jeu.v1` validé."""

    nom: str
    budget_credits_reference: int
    questions: tuple[QuestionDuJeu, ...]


# --- métriques ------------------------------------------------------------------------------------


def _verifier_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k doit être un entier d'au moins 1")


def pertinentes_retrouvees(rendues: Sequence[str], pertinentes: Sequence[str], k: int) -> int:
    """Nombre de vidéos pertinentes (sans doublon) parmi les `k` premières rendues."""
    _verifier_k(k)
    return len(set(rendues[:k]) & set(pertinentes))


def rappel_a_k(rendues: Sequence[str], pertinentes: Sequence[str], k: int) -> float:
    """Part des vidéos pertinentes retrouvées parmi les `k` premières rendues (0 à 1).

    Sans vidéo pertinente attendue, la question n'a rien à retrouver : le rappel est indéfini et refusé.
    """
    attendues = set(pertinentes)
    if not attendues:
        raise ValueError("aucune vidéo pertinente attendue : rappel indéfini")
    return pertinentes_retrouvees(rendues, pertinentes, k) / len(attendues)


def ndcg_a_k(rendues: Sequence[str], pertinentes: Sequence[str], k: int) -> float:
    """nDCG@k à gain binaire : gain cumulé actualisé (1 / log2(rang + 1)) sur le meilleur classement possible.

    Une vidéo rendue deux fois ne compte qu'à son premier rang. Résultat de 0 à 1 ; 1 quand toutes les
    pertinentes tiennent en tête de liste.
    """
    _verifier_k(k)
    attendues = set(pertinentes)
    if not attendues:
        raise ValueError("aucune vidéo pertinente attendue : nDCG indéfini")
    vues: set[str] = set()
    dcg = 0.0
    for rang, identifiant in enumerate(rendues[:k], start=1):
        if identifiant in vues:
            continue
        vues.add(identifiant)
        if identifiant in attendues:
            dcg += 1 / math.log2(rang + 1)
    ideal = sum(1 / math.log2(rang + 1) for rang in range(1, min(k, len(attendues)) + 1))
    return dcg / ideal


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation, espaces réduits : base de la recherche d'un fait."""
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return " ".join(re.sub(r"[\W_]+", " ", sans_accents).split())


def fait_couvert(fait: str, textes: Sequence[str]) -> bool:
    """Vrai si le fait figure tel quel (casse, accents et ponctuation ignorés) dans un des textes."""
    cherche = normaliser(fait)
    if not cherche:
        return False
    return any(f" {cherche} " in f" {normaliser(texte)} " for texte in textes)


def faits_couverts(faits: Sequence[str], textes: Sequence[str]) -> int:
    """Nombre de faits attendus retrouvés dans les textes (transcription, texte à l'écran, légende)."""
    return sum(1 for fait in faits if fait_couvert(fait, textes))


# --- jeu `jeu.v1` ---------------------------------------------------------------------------------


def _texte(valeur: Any, chemin: str, maximum: int | None = None) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise JeuInvalide(f"{chemin} : texte non vide attendu")
    if maximum is not None and len(valeur) > maximum:
        raise JeuInvalide(f"{chemin} : {maximum} caractères au plus")
    return valeur.strip()


def _liste_de_textes(valeur: Any, chemin: str, minimum: int, maximum: int | None) -> tuple[str, ...]:
    if not isinstance(valeur, list):
        raise JeuInvalide(f"{chemin} : liste attendue")
    if len(valeur) < minimum or (maximum is not None and len(valeur) > maximum):
        borne = f"{minimum} à {maximum}" if maximum is not None else f"au moins {minimum}"
        raise JeuInvalide(f"{chemin} : {borne} élément(s) attendu(s), {len(valeur)} reçu(s)")
    textes = tuple(_texte(element, f"{chemin}[{i}]") for i, element in enumerate(valeur))
    if len(set(textes)) != len(textes):
        raise JeuInvalide(f"{chemin} : doublon")
    return textes


def _cles(objet: Any, chemin: str, attendues: set[str]) -> Mapping[str, Any]:
    if not isinstance(objet, dict):
        raise JeuInvalide(f"{chemin} : objet attendu")
    manquantes, inconnues = attendues - set(objet), set(objet) - attendues
    if manquantes:
        raise JeuInvalide(f"{chemin} : champ(s) manquant(s) {sorted(manquantes)}")
    if inconnues:
        raise JeuInvalide(f"{chemin} : champ(s) inconnu(s) {sorted(inconnues)}")
    return objet


def valider_jeu(document: Any) -> Jeu:
    """Valide un document `jeu.v1` ; lève `JeuInvalide` à la première anomalie.

    Un jeu a un nom, un budget de crédits de référence (entier, tout le jeu) et au moins une question ;
    chaque question a un identifiant unique, le texte à envoyer au service, un à trois faits attendus et
    au moins une vidéo pertinente trouvée à la main (identifiants du service).
    """
    jeu = _cles(document, "jeu", CLES_JEU)
    if jeu["version"] != VERSION_JEU:
        raise JeuInvalide(f"jeu.version : « {VERSION_JEU} » attendu")
    nom = _texte(jeu["nom"], "jeu.nom", 200)
    budget = jeu["budget_credits_reference"]
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise JeuInvalide("jeu.budget_credits_reference : entier positif ou nul attendu")
    brutes = jeu["questions"]
    if not isinstance(brutes, list) or not brutes:
        raise JeuInvalide("jeu.questions : au moins une question attendue")
    questions: list[QuestionDuJeu] = []
    for i, brute in enumerate(brutes):
        chemin = f"questions[{i}]"
        q = _cles(brute, chemin, CLES_QUESTION)
        faits = _liste_de_textes(q["faits_attendus"], f"{chemin}.faits_attendus", FAITS_MIN, FAITS_MAX)
        videos = _liste_de_textes(q["videos_pertinentes"], f"{chemin}.videos_pertinentes", 1, None)
        questions.append(
            QuestionDuJeu(
                identifiant=_texte(q["id"], f"{chemin}.id", 64),
                question=_texte(q["question"], f"{chemin}.question", QUESTION_MAX),
                faits_attendus=faits,
                videos_pertinentes=videos,
            )
        )
    identifiants = [q.identifiant for q in questions]
    if len(set(identifiants)) != len(identifiants):
        raise JeuInvalide("jeu.questions : identifiant en double")
    return Jeu(nom=nom, budget_credits_reference=budget, questions=tuple(questions))
