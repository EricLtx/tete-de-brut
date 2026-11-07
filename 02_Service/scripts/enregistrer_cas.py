"""Enregistre le cas réel : interroge Oriane avec la clé de l'humain et écrit le fichier du cas, hors Git.

    python scripts/enregistrer_cas.py requetes.json [--sortie cas/cas.json] [--env .env]

`requetes.json` : {"phrases": ["…", "…"], "comptes": ["…"], "fenetre": {"debut": "2026-10-01T00:00:00+00:00",
"fin": "2026-11-06T23:59:59+00:00"}, "plateformes": ["tiktok"]} ; `comptes`, `fenetre` et `plateformes`
sont facultatifs. La clé est lue dans l'environnement (`ORIANE_API_KEY`) ou dans le `.env` du service,
jamais en argument. Une phrase de moins de trois mots est refusée (RG-02) ; un champ de tiers, une image
ou une vidéo dans le résultat font refuser l'écriture. Une page de 100 résultats au plus, environ 15 crédits.
Codes de sortie : 0 écrit, 1 refusé ou en échec (la raison est écrite sur la sortie d'erreur).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

RACINE_SERVICE = Path(__file__).resolve().parent.parent
if str(RACINE_SERVICE) not in sys.path:
    sys.path.insert(0, str(RACINE_SERVICE))

from app import base, cas  # noqa: E402
from app.config import Configuration  # noqa: E402
from app.modeles import Fenetre  # noqa: E402
from app.oriane import ErreurOriane, rechercher  # noqa: E402


def charger_env(chemin: Path) -> None:
    """Lit un fichier `.env` (lignes CLE=valeur) sans écraser l'environnement déjà posé."""
    if not chemin.is_file():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, _, valeur = ligne.partition("=")
        os.environ.setdefault(nom.strip(), valeur.strip().strip("\"'"))


def lire_requetes(chemin: Path) -> dict[str, Any]:
    """Fichier de requêtes : phrases (obligatoire), comptes, plateformes, fenêtre."""
    try:
        requetes = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise cas.CasInvalide(f"fichier de requêtes illisible : {chemin.name}") from exc
    if not isinstance(requetes, dict) or set(requetes) - {"phrases", "comptes", "plateformes", "fenetre"}:
        raise cas.CasInvalide("le fichier de requêtes ne porte que phrases, comptes, plateformes et fenetre")
    return requetes


async def enregistrer(
    config: Configuration,
    requetes: dict[str, Any],
    sortie: Path | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[Path, cas.CasEnregistre]:
    """Interroge Oriane puis écrit le cas ; lève `CasInvalide` ou `ErreurOriane` avec une raison lisible."""
    phrases = requetes.get("phrases") or []
    raison = cas.verifier_phrases(phrases)
    if raison:
        raise cas.CasInvalide(raison)
    if not config.oriane_cle:
        raise cas.CasInvalide("ORIANE_API_KEY absente : définir la clé dans l'environnement ou le .env")
    fenetre = Fenetre.model_validate(requetes["fenetre"]) if requetes.get("fenetre") else None
    comptes, plateformes = requetes.get("comptes") or [], requetes.get("plateformes") or []
    base.configurer(config.chemin_base)
    base.initialiser()
    resultat = await rechercher(
        phrases, comptes, fenetre, config=config, plateformes=plateformes, transport=transport
    )
    if not resultat.videos:
        raise cas.CasInvalide("Oriane n'a rendu aucune vidéo exploitable : rien à enregistrer")
    document = cas.construire_document(
        enregistre_le=datetime.now(UTC),
        phrases=phrases,
        comptes=comptes,
        plateformes=plateformes,
        fenetre=fenetre,
        credits_estimes=resultat.credits_estimes,
        videos=resultat.videos,
    )
    chemin = sortie or cas.fichier_cas(config)
    return chemin, cas.ecrire_fichier(chemin, document)


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Enregistre le cas réel (clé Oriane lue dans l'environnement)."
    )
    analyseur.add_argument("requetes", type=Path, help="fichier JSON des phrases, comptes et fenêtre")
    analyseur.add_argument(
        "--sortie", type=Path, default=None, help="fichier du cas (défaut : CHEMIN_CAS/cas.json)"
    )
    analyseur.add_argument("--env", type=Path, default=RACINE_SERVICE / ".env", help="fichier .env à lire")
    arguments = analyseur.parse_args(argv)
    charger_env(arguments.env)
    try:
        config = Configuration.depuis_environnement()
        requetes = lire_requetes(arguments.requetes)
        chemin, cas_ecrit = asyncio.run(enregistrer(config, requetes, arguments.sortie))
    except (cas.CasInvalide, ErreurOriane) as exc:
        print(f"refusé : {exc.raison}", file=sys.stderr)
        return 1
    print(
        f"cas enregistré : {chemin} ({len(cas_ecrit.videos)} vidéos, "
        f"{cas_ecrit.credits_estimes} crédits estimés, {len(cas_ecrit.phrases)} phrases)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
