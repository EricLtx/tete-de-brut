"""Fiche de vérification `fiche.v1` (S08) : construction depuis une comparaison, gestes, décision.

La machine assemble les sources, les indices et les limites ; elle ne pré-remplit jamais le
constat (vide à la création) et ne décide rien. Les gestes du journaliste (versions tranchées,
constat, décision) sont inscrits au journal de la fiche avec leur heure.
"""

from __future__ import annotations

from app.erreurs import ErreurApi
from app.modeles import (
    LIMITE_TRANSCRIPTIONS,
    Decision,
    DemandeDecision,
    Ecart,
    Fiche,
    GesteFiche,
    ModificationFiche,
    PlusAncienneVersion,
    Segment,
    VersionFiche,
    Video,
)
from app.resume import indices_de_transformation, libelle, resumer

TYPE_DOCUMENT = "fiche"

NON_CHERCHE: tuple[str, ...] = (
    "Autres plateformes que Instagram, TikTok et YouTube.",
    "Vidéos supprimées avant la recherche.",
    "Comptes privés.",
    "Vidéos publiées hors de la fenêtre de la requête.",
    "Résultats au-delà de ceux consultés.",
)

LIMITES: tuple[str, ...] = (
    LIMITE_TRANSCRIPTIONS,
    "Vues et interactions selon Oriane, non recomptées.",
    "Heure du passage dans la vidéo non fournie au niveau default.",
    "Comparaison limitée aux deux versions choisies ; d'autres versions peuvent exister.",
    "L'écart décrit ce qui diffère, il ne dit pas pourquoi.",
)


def identifiant_fiche(comparaison: str) -> str:
    """Une fiche par comparaison : identifiant dérivé de celui de la comparaison."""
    return f"fic-{comparaison.removeprefix('cmp-')}"


def requete_de(source: Video, reprise: Video) -> str:
    """Requêtes qui ont trouvé les deux versions (à défaut, l'une ou l'autre), en clair."""
    communes = [r for r in source.requetes_trouvees if r in reprise.requetes_trouvees]
    toutes = communes or list(dict.fromkeys(source.requetes_trouvees + reprise.requetes_trouvees))
    return " ; ".join(toutes)


def version_de(video: Video) -> VersionFiche:
    """Une version de la fiche, à trancher : lien, compte, date et vues selon Oriane."""
    return VersionFiche(
        video=video.identifiant,
        lien=video.lien,
        compte=video.compte,
        date=video.publie_le,
        vues_selon_oriane=video.vues_selon_oriane,
    )


def construire_fiche(
    comparaison: Ecart, source: Video, reprise: Video, *, mode: str, enregistre_le: str | None, heure: str
) -> Fiche:
    """Fiche neuve : versions à trancher, indices et résumé du gabarit, constat vide, aucune décision."""
    plus_ancienne = min((source, reprise), key=lambda v: v.publie_le)
    return Fiche.model_validate(
        {
            "mode": mode,
            "enregistre_le": enregistre_le,
            "identifiant": identifiant_fiche(comparaison.identifiant),
            "comparaison": comparaison.identifiant,
            "requete": requete_de(source, reprise),
            "versions": [version_de(source), version_de(reprise)],
            "indices_de_transformation": indices_de_transformation(comparaison),
            "plus_ancienne_version": PlusAncienneVersion(
                video=plus_ancienne.identifiant, publie_le=plus_ancienne.publie_le
            ),
            "non_cherche": [libelle(t) for t in NON_CHERCHE],
            "limites": [libelle(t) for t in LIMITES],
            "resume": resumer(comparaison),
            "constat": "",
            "decision": None,
            "journal": [
                GesteFiche(
                    heure=heure, geste="creation", detail=f"depuis la comparaison {comparaison.identifiant}"
                )
            ],
        }
    )


def modifier(fiche: Fiche, modification: ModificationFiche, *, heure: str) -> Fiche:
    """Applique les gestes du journaliste : versions tranchées (avec note) et constat, sans filtre."""
    donnees = fiche.model_copy(deep=True)
    par_video = {v.video: v for v in donnees.versions}
    for tranchee in modification.versions or []:
        version = par_video.get(tranchee.video)
        if version is None:
            raise ErreurApi(
                "validation", f"La vidéo {tranchee.video} n'est pas une des deux versions de la fiche.", 422
            )
        version.etat = tranchee.etat
        version.note = tranchee.note
        donnees.journal.append(
            GesteFiche(heure=heure, geste="version_tranchee", detail=f"{tranchee.video} : {tranchee.etat}")
        )
    if modification.constat is not None:
        donnees.constat = modification.constat
        donnees.journal.append(GesteFiche(heure=heure, geste="constat_ecrit"))
    return Fiche.model_validate(donnees.model_dump(mode="json"))


def decider(fiche: Fiche, demande: DemandeDecision, *, heure: str) -> Fiche:
    """Enregistre la décision prise par une personne ; l'heure est posée par le service."""
    donnees = fiche.model_copy(deep=True)
    donnees.decision = Decision(valeur=demande.valeur, role=demande.role, note=demande.note, heure=heure)
    donnees.journal.append(
        GesteFiche(heure=heure, geste="decision", detail=f"{demande.valeur} ({demande.role})")
    )
    return Fiche.model_validate(donnees.model_dump(mode="json"))


def verifier_exportable(fiche: Fiche) -> None:
    """Refuse l'export (409) tant que décision, versions tranchées ou constat manquent."""
    if fiche.decision is None:
        raise ErreurApi("decision_manquante", "La fiche n'a pas encore de décision : export refusé.", 409)
    a_trancher = [v.video for v in fiche.versions if v.etat == "a_trancher"]
    if a_trancher:
        raise ErreurApi(
            "version_non_tranchee",
            f"Version encore à trancher ({', '.join(a_trancher)}) : export refusé.",
            409,
        )
    if not fiche.constat.strip():
        raise ErreurApi("constat_manquant", "Le constat du journaliste est vide : export refusé.", 409)


def segments_libelles(fiche: Fiche) -> list[Segment]:
    """Tous les segments `libelle` de la fiche (pour vérifier le filtre)."""
    tous = fiche.indices_de_transformation + fiche.non_cherche + fiche.limites + fiche.resume.segments
    return [s for s in tous if s.type == "libelle"]
