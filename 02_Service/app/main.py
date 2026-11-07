"""Application FastAPI : passerelle (CORS, clé de démonstration, enveloppe d'erreur) et route de santé.

Les responsabilités transverses vivent ici, dans des intergiciels et gestionnaires, jamais dans les
fichiers de routes. Le routeur `/v1` porte les routes du contrat `api.v1`, branchées ici une fois.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__, base, cas
from app.config import Configuration
from app.erreurs import installer_gestionnaires
from app.modeles import API_V1
from app.routes import comparaisons, etat, fiches, radar, videos
from app.securite import EN_TETE_CLE_DEMO, exiger_cle_demo

journal = logging.getLogger("tete_de_brut")

routeur_v1 = APIRouter(prefix="/v1")
for module in (etat, radar, videos, comparaisons, fiches):
    routeur_v1.include_router(module.routeur)


def creer_application(config: Configuration | None = None) -> FastAPI:
    """Construit l'application ; sans argument, la configuration vient de l'environnement."""
    config = config or Configuration.depuis_environnement()
    base.configurer(config.chemin_base)

    @asynccontextmanager
    async def cycle_de_vie(application: FastAPI) -> AsyncIterator[None]:
        base.configurer(config.chemin_base)
        base.initialiser()
        if config.mode == "enregistre":
            try:
                cas.charger(config, avec_videos=True)
            except cas.CasInvalide as exc:
                journal.warning("cas enregistré non chargé : %s", exc.raison)
        if not config.cle_demo:
            avertissement = "CLE_DEMO vide : le service est ouvert, toute écriture sous /v1 est acceptée"
            journal.warning(avertissement)
            base.consigner(route="demarrage", cible=avertissement, mode=config.mode)
        yield

    app = FastAPI(
        title="Tête de Brut. — service de démonstration",
        version=API_V1,
        lifespan=cycle_de_vie,
    )
    app.state.config = config
    installer_gestionnaires(app)

    # Ordre d'empilement : le dernier ajouté est le plus externe. CORS enveloppe la clé de
    # démonstration, donc une réponse 401 porte aussi les en-têtes CORS et la pré-vérification passe.
    app.middleware("http")(exiger_cle_demo)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.origines_autorisees),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=[EN_TETE_CLE_DEMO, "Content-Type"],
    )

    @app.get("/sante", include_in_schema=False)
    async def sante() -> dict[str, str | None]:
        """Sonde de vie, hors contrat versionné."""
        return {"etat": "ok", "version": __version__, "mode": app.state.config.mode, "enregistre_le": None}

    app.include_router(routeur_v1)
    return app


app = creer_application()
