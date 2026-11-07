"""Export de la fiche en page HTML lisible (S08), verrouillé tant qu'un geste manque.

Constat en tête ; chaque indice avec les liens des deux versions ; extraits de 40 mots au plus ;
rôle et heure de la décision ; mode et date. Tout texte venu des vidéos ou du journaliste est
échappé (jamais interprété) ; les propos rapportés sont balisés `class="citation"` et les textes
du journaliste `class="journaliste"`, seuls endroits où un libellé refusé peut figurer.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from app.fiche import verifier_exportable
from app.modeles import Fiche, Segment, VersionFiche
from app.resume import extrait

LIBELLES_DECISION = {
    "a_verifier": "à vérifier",
    "ne_pas_amplifier": "ne pas amplifier",
    "pret_a_traiter": "prêt à traiter",
}
LIBELLES_ETAT = {"a_trancher": "à trancher", "confirmee": "confirmée", "ecartee": "écartée"}

_STYLE = (
    "body{font-family:system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;"
    "line-height:1.5;color:#111;background:#fff}"
    "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:1.5rem}"
    ".constat{border-left:4px solid #111;padding:.5rem 1rem;background:#f4f4f4;white-space:pre-wrap}"
    ".citation{font-style:italic}.meta{color:#555;font-size:.9rem}"
)


def _e(texte: object) -> str:
    return escape(str(texte), quote=True)


def _date(valeur: datetime | None) -> str:
    return valeur.isoformat(timespec="minutes") if valeur is not None else "non fournie"


def _lien(url: str, texte: str) -> str:
    """Lien cliquable seulement en http(s) ; sinon l'adresse est affichée en texte."""
    if url.startswith(("https://", "http://")):
        return f'<a href="{_e(url)}" rel="noopener noreferrer">{_e(texte)}</a>'
    return f"{_e(texte)} ({_e(url)})"


def _segment(segment: Segment) -> str:
    if segment.type == "citation":
        return f'<q class="citation">{_e(extrait(segment.texte))}</q>'
    return _e(segment.texte)


def _segments_en_paragraphes(segments: list[Segment]) -> str:
    return "".join(f"<li>{_segment(s)}</li>" for s in segments)


def _indices(fiche: Fiche, source: VersionFiche, reprise: VersionFiche) -> str:
    """Un élément de liste par indice : une phrase fixe et ses extraits, puis les deux liens."""
    groupes: list[list[Segment]] = []
    for segment in fiche.indices_de_transformation:
        nouvelle_phrase = segment.type == "libelle" and not segment.texte.startswith("dans la reprise")
        if nouvelle_phrase or not groupes:
            groupes.append([segment])
        else:
            groupes[-1].append(segment)
    liens = f"{_lien(source.lien, 'version source')} · {_lien(reprise.lien, 'version reprise')}"
    elements = [
        "<li>" + " ".join(_segment(s) for s in groupe) + f' <span class="meta">({liens})</span></li>'
        for groupe in groupes
    ]
    return "".join(elements)


def _version(titre: str, version: VersionFiche) -> str:
    vues = (
        f"{version.vues_selon_oriane} vues selon Oriane"
        if version.vues_selon_oriane is not None
        else "vues non fournies par Oriane"
    )
    note = f' — note : <span class="journaliste">{_e(version.note)}</span>' if version.note else ""
    return (
        f"<li><strong>{_e(titre)}</strong> : {_lien(version.lien, version.lien)} — compte "
        f'<span class="citation">{_e(version.compte)}</span>, publiée le {_e(_date(version.date))}, '
        f"{_e(vues)} — {_e(LIBELLES_ETAT[version.etat])}{note}</li>"
    )


def exporter(fiche: Fiche, *, exporte_le: str) -> str:
    """Page HTML de la fiche ; lève une erreur 409 tant que l'export n'est pas permis."""
    verifier_exportable(fiche)
    decision = fiche.decision
    assert decision is not None  # garanti par verifier_exportable
    source, reprise = fiche.versions
    mode = "en direct" if fiche.mode == "direct" else f"enregistré le {_date(fiche.enregistre_le)}"
    plus_ancienne = ""
    if fiche.plus_ancienne_version is not None:
        p = fiche.plus_ancienne_version
        plus_ancienne = (
            f"<h2>Plus ancienne version</h2><p>{_e(p.libelle)} : {_e(p.video)}, "
            f"publiée le {_e(_date(p.publie_le))} (selon Oriane).</p>"
        )
    note_decision = f' — note : <span class="journaliste">{_e(decision.note)}</span>' if decision.note else ""
    journal = "".join(
        f"<li>{_e(_date(g.heure))} — {_e(g.geste)}"
        + (f' : <span class="journaliste">{_e(g.detail)}</span>' if g.detail else "")
        + "</li>"
        for g in fiche.journal
    )
    return (
        "<!doctype html>\n"
        '<html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Fiche de vérification {_e(fiche.identifiant)}</title><style>{_STYLE}</style></head>"
        "<body>"
        f'<section id="constat"><h1>Constat du journaliste</h1>'
        f'<div class="constat journaliste">{_e(fiche.constat)}</div></section>'
        f'<section id="decision"><h2>Décision</h2><p><strong>{_e(LIBELLES_DECISION[decision.valeur])}'
        f'</strong> — rôle : <span class="journaliste">{_e(decision.role)}</span>, '
        f"le {_e(_date(decision.heure))}{note_decision}</p></section>"
        f'<p class="meta">Fiche {_e(fiche.identifiant)} — mode : {_e(mode)} — exportée le {_e(exporte_le)} '
        f"— éléments rapportés selon Oriane, à recouper par la rédaction.</p>"
        f'<h2>Requête</h2><p><q class="citation">{_e(extrait(fiche.requete))}</q></p>'
        f"<h2>Versions</h2><ul>{_version('Source', source)}{_version('Reprise', reprise)}</ul>"
        f"<h2>Indices de transformation (selon Oriane)</h2><ul>{_indices(fiche, source, reprise)}</ul>"
        f"{plus_ancienne}"
        f"<h2>Résumé ({_e(fiche.resume.methode)})</h2>"
        f"<ul>{_segments_en_paragraphes(fiche.resume.segments)}</ul>"
        f"<h2>Non cherché</h2><ul>{_segments_en_paragraphes(fiche.non_cherche)}</ul>"
        f"<h2>Limites</h2><ul>{_segments_en_paragraphes(fiche.limites)}</ul>"
        f'<h2>Journal de la fiche</h2><ul class="meta">{journal}</ul>'
        "</body></html>\n"
    )
