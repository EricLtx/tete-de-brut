"""Pertinence des vidéos d'un récit jugée par le modèle de langue (F021, S18)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app import base, pertinence
from app.config import Configuration
from app.erreurs import ErreurApi
from app.modeles import VIDEO_V1, ClassementPertinence, DemandePertinence, Recit, Video
from app.recits import TYPE_VIDEO, calculer_recits
from app.routes import erreurs

routeur = APIRouter(tags=["pertinence"])

ROUTE_JOURNAL = "pertinence:classement"


def question_du_recit(recit: Recit) -> str:
    """Question par défaut : la phrase surveillée, suivie de ses variantes si le récit en porte.

    `variantes` est un champ facultatif que la recherche peut ajouter au récit : il est lu sans en dépendre.
    """
    variantes = [v for v in (getattr(recit, "variantes", None) or []) if isinstance(v, str) and v.strip()]
    if not variantes:
        return recit.phrase_surveillee
    return f"{recit.phrase_surveillee} (variantes : {' ; '.join(variantes)})"


def _classee_pour(document: dict[str, Any] | None, question: str) -> bool:
    """Vrai si la vidéo porte déjà une pertinence jugée pour cette même question."""
    annotation = (document or {}).get("pertinence")
    return isinstance(annotation, dict) and annotation.get("question") == question


def _avertissement(config: Configuration, sans_jugement: int, hors_limite: int, echecs: int) -> str | None:
    """Limite du classement en clair ; `None` quand tout le récit est jugé et que le modèle a répondu."""
    if not config.modele_langue_cle:
        return "Clé du modèle de langue absente : aucun appel, les vidéos non classées le restent."
    if config.pertinence_mode == "aucun":
        return "PERTINENCE_MODE=aucun : aucun appel, les vidéos non classées le restent."
    parties = []
    if hors_limite:
        parties.append(f"{hors_limite} au-delà des {config.pertinence_max_videos} plus récentes")
    if echecs:
        parties.append(f"{echecs} sans réponse utilisable du modèle, voir le journal")
    if not sans_jugement:
        return f"Jugement précédent gardé : {parties[-1]}." if echecs else None
    detail = f" ({' ; '.join(parties)})" if parties else ""
    return f"{sans_jugement} vidéo(s) sans jugement{detail}."


def _consigner(question: str, mode: str, comptes: dict[str, int], debut: float) -> None:
    """Ligne `pertinence:classement` au journal ; un refus du journal ne fait jamais échouer la route."""
    try:
        base.consigner(
            route=ROUTE_JOURNAL,
            cible=question,
            resultats=comptes,
            credits_estimes=None,
            duree_ms=round((time.monotonic() - debut) * 1000, 1),
            mode=mode,
        )
    except Exception:  # noqa: BLE001 - le journal ne doit jamais faire échouer un classement
        pertinence.journal.warning("pertinence : journal indisponible")


@routeur.post(
    "/recits/{id}/pertinence",
    response_model=ClassementPertinence,
    summary="Juger la pertinence des vidéos d'un récit pour une question, par le modèle de langue",
    responses=erreurs(401, 404, 422, 501),
)
async def classer_les_videos(
    id: str, request: Request, demande: DemandePertinence | None = None
) -> ClassementPertinence:
    """Annote chaque vidéo du récit (`pertinence`) : `forte`, `faible` ou `hors_sujet`, avec un motif court.

    Aucune vidéo n'est supprimée ni réordonnée. Les `PERTINENCE_MAX_VIDEOS` plus récentes sont jugées ;
    une vidéo déjà jugée pour la même question n'est pas renvoyée au modèle, sauf `forcer`. Sans clé du
    modèle ou en mode `aucun`, aucun appel. Une panne du modèle laisse les vidéos sans jugement (jamais 5xx).
    """
    debut = time.monotonic()
    config: Configuration = request.app.state.config
    recits, _ = calculer_recits(config.mode)
    recit = next((r for r in recits if r.identifiant == id), None)
    if recit is None:
        raise ErreurApi("introuvable", f"Aucun récit « {id} » dans le radar.", 404)
    demande = demande or DemandePertinence()
    question = (demande.question or "").strip() or question_du_recit(recit)

    # Les vidéos du récit présentes en base (un document lu une fois), les plus récentes d'abord.
    documents: dict[str, dict[str, Any]] = {}
    presentes: list[Video] = []
    for identifiant in recit.videos:
        document = base.lire(TYPE_VIDEO, identifiant)
        if document is None:
            continue
        try:
            presentes.append(Video.model_validate(document))
        except ValidationError:
            continue
        documents[identifiant] = document
    presentes.sort(key=lambda v: (v.publie_le, v.identifiant), reverse=True)
    retenues = presentes[: config.pertinence_max_videos]
    hors_limite = len(presentes) - len(retenues)
    a_juger = [v for v in retenues if demande.forcer or not _classee_pour(documents[v.identifiant], question)]

    # L'appel au modèle est bloquant : il part dans un fil pour ne pas retenir la boucle d'événements.
    jugees = await run_in_threadpool(pertinence.classer, question, a_juger, config)
    for identifiant, annotation in jugees.items():
        # Le document est relu juste avant l'écriture : seul le champ `pertinence` change.
        courant = base.lire(TYPE_VIDEO, identifiant)
        if courant is not None:
            documents[identifiant] = {**courant, "pertinence": annotation.model_dump(mode="json")}
            base.ecrire(TYPE_VIDEO, identifiant, VIDEO_V1, documents[identifiant])

    # Les comptes disent l'état de la base après l'appel, vidéos jugées plus tôt comprises.
    niveaux = {"forte": 0, "faible": 0, "hors_sujet": 0}
    for document in documents.values():
        if _classee_pour(document, question):
            niveaux[document["pertinence"]["niveau"]] += 1
    classees = sum(niveaux.values())
    non_classees = len(recit.videos) - classees
    echecs = (len(a_juger) - len(jugees)) if config.pertinence_par_modele else 0
    comptes = {
        "classees": classees,
        "fortes": niveaux["forte"],
        "faibles": niveaux["faible"],
        "hors_sujet": niveaux["hors_sujet"],
        "non_classees": non_classees,
    }
    _consigner(question, config.mode, comptes, debut)
    return ClassementPertinence(
        mode=config.mode,  # type: ignore[arg-type]
        enregistre_le=recit.enregistre_le,
        identifiant=id,
        question=question,
        modele=config.pertinence_modele_id if config.pertinence_par_modele else "",
        classees=classees,
        fortes=niveaux["forte"],
        faibles=niveaux["faible"],
        hors_sujet=niveaux["hors_sujet"],
        non_classees=non_classees,
        avertissement=_avertissement(config, non_classees, hors_limite, max(echecs, 0)),
    )
