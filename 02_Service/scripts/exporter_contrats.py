"""Exporte les contrats du service dans `contrats/` : un JSON Schema par contrat et l'OpenAPI `api.v1`.

    python scripts/exporter_contrats.py             # écrit les fichiers
    python scripts/exporter_contrats.py --verifier  # sort 1 si un fichier diffère de l'application

Format figé : JSON indenté de 2, clés triées, caractères non ASCII gardés, fin de ligne LF.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RACINE_SERVICE = Path(__file__).resolve().parent.parent
if str(RACINE_SERVICE) not in sys.path:
    sys.path.insert(0, str(RACINE_SERVICE))

from app.config import Configuration  # noqa: E402
from app.main import creer_application  # noqa: E402
from app.modeles import API_V1, CONTRATS, schema_contrat  # noqa: E402

DOSSIER_CONTRATS = RACINE_SERVICE / "contrats"


def en_texte(objet: Any) -> str:
    """Sérialisation figée d'un contrat."""
    return json.dumps(objet, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def contrats_attendus() -> dict[str, str]:
    """Nom de fichier → contenu attendu, d'après le code de l'application."""
    attendus = {f"{nom}.schema.json": en_texte(schema_contrat(nom)) for nom in CONTRATS}
    application = creer_application(Configuration.depuis_environnement({}))
    attendus[f"{API_V1}.json"] = en_texte(application.openapi())
    return attendus


def main(arguments: list[str] | None = None) -> int:
    """Écrit les contrats, ou vérifie qu'ils sont à jour (`--verifier`)."""
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--verifier", action="store_true", help="vérifier sans écrire ; 1 si écart")
    options = analyseur.parse_args(arguments)

    ecarts = []
    for nom, contenu in contrats_attendus().items():
        chemin = DOSSIER_CONTRATS / nom
        if options.verifier:
            # Lecture en mode texte : une copie de travail en CRLF (Windows) reste égale.
            actuel = chemin.read_text(encoding="utf-8") if chemin.exists() else None
            if actuel != contenu:
                ecarts.append(nom)
        else:
            DOSSIER_CONTRATS.mkdir(parents=True, exist_ok=True)
            chemin.write_text(contenu, encoding="utf-8", newline="\n")
            print(f"écrit : contrats/{nom}")
    if ecarts:
        print("contrats à régénérer (python scripts/exporter_contrats.py) : " + ", ".join(ecarts))
        return 1
    if options.verifier:
        print("contrats à jour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
