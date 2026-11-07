"""Vidéos lues chez Oriane (rempli par S03)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modeles import Video
from app.routes import erreurs, non_implemente

routeur = APIRouter(tags=["vidéos"])


@routeur.get(
    "/videos/{id}",
    response_model=Video,
    summary="Une vidéo : compte, date, vues selon Oriane, légende, transcription et texte à l'écran",
    responses=erreurs(404, 422, 501),
)
async def lire_video(id: str) -> Video:
    """Vidéo `video.v1`, transcription et texte à l'écran attribués à Oriane, sans donnée de tiers."""
    raise non_implemente("GET /v1/videos/{id}")
