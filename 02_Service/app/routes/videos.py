"""Vidéos lues chez Oriane : `GET /v1/videos/{id}` sert une vidéo écrite en base par `app/oriane.py`."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import base
from app.erreurs import ErreurApi
from app.modeles import Video
from app.recits import lire_videos
from app.routes import erreurs

routeur = APIRouter(tags=["vidéos"])


@routeur.get(
    "/videos/{id}",
    response_model=Video,
    summary="Une vidéo : compte, date, vues selon Oriane, légende, transcription et texte à l'écran",
    responses=erreurs(404, 422, 501),
)
async def lire_video(id: str, request: Request) -> Video:
    """Vidéo `video.v1`, transcription et texte à l'écran attribués à Oriane, sans donnée de tiers."""
    document = base.lire("video", id)
    if document is None:
        raise ErreurApi("introuvable", "Aucune vidéo n'a cet identifiant.", 404)
    # `mode` suit la configuration : une vidéo lue en mode enregistré n'est jamais servie « en direct ».
    direct = request.app.state.config.mode == "direct" and document.get("mode") == "direct"
    if direct:
        document["mode"], document["enregistre_le"] = "direct", None
    else:
        document["mode"] = "enregistre"
        document["enregistre_le"] = document.get("enregistre_le") or document["transcription"]["lue_le"]
    return lire_videos([document])[0]
