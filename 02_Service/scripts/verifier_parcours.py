"""Vérifie le parcours du journaliste contre un service lancé : une ligne OK ou KO par geste.

    python scripts/verifier_parcours.py --adresse http://localhost:8080 --origine http://localhost:5173

Neuf gestes, dans l'ordre : santé, radar, je cherche, vidéo, comparaison, fiche, décision, export,
en-tête CORS. Le script lit le radar du service (aucune actualisation, donc aucun crédit Oriane dépensé) ;
le geste « je cherche » prépare une recherche sur la phrase du premier récit (aucun appel), vérifie le
refus d'un nom seul (RG-02), et ne la lance que si le service est en mode enregistré (rien n'est dépensé)
ou si `--lancer-la-recherche` est donné (en direct, une page : 15 crédits). Il prend ensuite les
deux premières vidéos du premier récit et rejoue le parcours sur ce couple, pris dans l'ordre inverse
de celui de la démonstration pour ne pas toucher à la fiche qu'on y montre. Il écrit donc une
comparaison, une fiche, des versions tranchées, un constat et une décision « à vérifier » dans la base du
service vérifié.

Si `CLE_DEMO` est dans l'environnement du script, elle est envoyée dans `X-Cle-Demo`.
Sortie : neuf lignes sur la sortie standard ; code 0 seulement si les neuf sont OK, sinon 1.
Bibliothèque standard et `httpx` seulement : le script n'importe rien du service.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from typing import Any

import httpx

EN_TETE_CLE_DEMO = "X-Cle-Demo"
ORIGINE_HOSTILE = "https://origine-non-autorisee.invalid"
DELAI_S = 20.0
ROLE = "script de vérification du parcours"
CONSTAT = "Constat de vérification du parcours : écrit par le script, à ne pas reprendre."


class Echec(Exception):
    """Un geste du parcours n'est pas conforme : le message dit pourquoi, en une phrase."""


class Parcours:
    """Client du service et mémoire du parcours (identifiants rencontrés d'un geste au suivant)."""

    def __init__(self, client: httpx.Client, origine: str, cle: str) -> None:
        self.client = client
        self.origine = origine
        self.entetes = {EN_TETE_CLE_DEMO: cle} if cle else {}
        self.videos: list[dict[str, Any]] = []
        self.comparaison = ""
        self.fiche: dict[str, Any] = {}
        self.phrase = ""
        self.lancer_la_recherche = False

    def appeler(self, methode: str, chemin: str, attendus: tuple[int, ...] = (200,), **kwargs: Any) -> Any:
        """Appelle le service ; refuse un statut inattendu ou une réponse JSON sans `mode`."""
        entetes = {**self.entetes, **kwargs.pop("headers", {})}
        try:
            reponse = self.client.request(methode, chemin, headers=entetes, **kwargs)
        except httpx.HTTPError as exc:
            raise Echec(f"{methode} {chemin} : service injoignable ({type(exc).__name__})") from exc
        if reponse.status_code not in attendus:
            raise Echec(f"{methode} {chemin} : code {reponse.status_code}{self._cause(reponse)}")
        if "application/json" not in reponse.headers.get("content-type", ""):
            return reponse
        corps = reponse.json()
        if not isinstance(corps, dict) or corps.get("mode") not in ("direct", "enregistre"):
            raise Echec(f"{methode} {chemin} : champ mode absent de la réponse")
        return corps

    @staticmethod
    def _cause(reponse: httpx.Response) -> str:
        try:
            corps = reponse.json()
            return f" ({corps['erreur']})"
        except (ValueError, KeyError, TypeError):
            return ""


def verifier_sante(p: Parcours) -> str:
    corps = p.appeler("GET", "/sante")
    if corps.get("etat") != "ok":
        raise Echec("etat différent de ok")
    return f"mode {corps['mode']}, version {corps.get('version')}"


def verifier_radar(p: Parcours) -> str:
    radar = p.appeler("GET", "/v1/radar")
    recits = radar.get("recits") or []
    if not recits:
        raise Echec("aucun récit : le service n'a pas de cas à montrer")
    mesures = [m for r in recits for m in r.get("mesures", [])]
    if not mesures:
        raise Echec("aucune mesure dans le radar")
    for m in mesures:
        if not str(m.get("methode", "")).strip() or not m.get("fenetre"):
            raise Echec(f"mesure {m.get('nom')} sans méthode ou sans fenêtre")
    p.videos = [{"identifiant": v} for v in recits[0].get("videos", [])]
    p.phrase = recits[0].get("phrase_surveillee", "")
    return f"{len(recits)} récit(s), {len(mesures)} mesure(s), mode {radar['mode']}"


def verifier_recherche(p: Parcours) -> str:
    if not p.phrase:
        raise Echec("pas de phrase surveillée au geste précédent")
    prepare = p.appeler("POST", "/v1/recherches/preparer", json={"question": f"« {p.phrase} »"})
    if prepare.get("refus") is not None or prepare.get("filtres", {}).get("phrases") != [p.phrase]:
        raise Echec("la préparation ne rend pas la phrase du cas en filtre, sans refus")
    if not prepare.get("requete_en_clair") or not prepare.get("cout_estime", {}).get("methode"):
        raise Echec("la préparation ne dit ni la requête en clair ni la méthode du coût")
    refus = p.appeler("POST", "/v1/recherches/preparer", json={"question": "Jean Dupont"})
    if (refus.get("refus") or {}).get("code") != "nom_seul":
        raise Echec("RG-02 : le seul nom d'une personne n'est pas refusé")
    detail = f"{prepare['cout_estime']['credits_estimes']} crédits estimés, nom seul refusé"
    if prepare["mode"] == "direct" and not p.lancer_la_recherche:
        return detail + ", recherche non lancée (--lancer-la-recherche)"
    lancee = p.appeler("POST", "/v1/recherches", attendus=(201,), json={"question": f"« {p.phrase} »"})
    if not (lancee.get("recit") or {}).get("videos"):
        raise Echec("la recherche lancée ne rend pas le récit de la phrase avec ses vidéos")
    return detail + f", lancée : récit de {len(lancee['recit']['videos'])} vidéo(s), mode {lancee['mode']}"


def verifier_video(p: Parcours) -> str:
    if len(p.videos) < 2:
        raise Echec("le premier récit n'a pas deux vidéos à comparer")
    p.videos = [p.appeler("GET", f"/v1/videos/{v['identifiant']}") for v in p.videos[:2]]
    for video in p.videos:
        for cle in ("transcription", "texte_ecran", "lien", "publie_le"):
            if not video.get(cle):
                raise Echec(f"vidéo {video.get('identifiant')} sans {cle}")
    return ", ".join(f"{v['identifiant']} ({v['compte']})" for v in p.videos)


def verifier_comparaison(p: Parcours) -> str:
    if len(p.videos) < 2:
        raise Echec("pas de vidéos lues au geste précédent")
    ancienne, recente = sorted(p.videos, key=lambda v: v["publie_le"])
    corps = p.appeler(
        "POST",
        "/v1/comparaisons",
        json={"video_source": recente["identifiant"], "video_reprise": ancienne["identifiant"]},
    )
    if corps.get("normalisation") != "mots.v1" or "operations" not in corps:
        raise Echec("la comparaison ne dit ni sa normalisation ni ses opérations")
    p.comparaison = corps["identifiant"]
    return f"{p.comparaison}, {len(corps['operations'])} opération(s) sur la parole"


def verifier_fiche(p: Parcours) -> str:
    if not p.comparaison:
        raise Echec("pas de comparaison au geste précédent")
    fiche = p.appeler("POST", "/v1/fiches", attendus=(200, 201), json={"comparaison": p.comparaison})
    if len(fiche.get("versions", [])) != 2 or not fiche.get("limites"):
        raise Echec("la fiche n'a pas deux versions et ses limites")
    p.fiche = fiche
    return f"{fiche['identifiant']}, deux versions, {len(fiche['limites'])} limite(s)"


def verifier_decision(p: Parcours) -> str:
    if not p.fiche:
        raise Echec("pas de fiche au geste précédent")
    chemin = f"/v1/fiches/{p.fiche['identifiant']}"
    versions = [
        {"video": v["video"], "etat": etat, "note": ""}
        for v, etat in zip(p.fiche["versions"], ("confirmee", "ecartee"), strict=True)
    ]
    p.appeler("PATCH", chemin, json={"versions": versions, "constat": CONSTAT})
    fiche = p.appeler("POST", f"{chemin}/decision", json={"valeur": "a_verifier", "role": ROLE, "note": ""})
    if not fiche.get("decision") or fiche["decision"].get("valeur") != "a_verifier":
        raise Echec("la décision n'est pas enregistrée sur la fiche")
    p.fiche = fiche
    return f"décision {fiche['decision']['valeur']} enregistrée par « {fiche['decision']['role']} »"


def verifier_export(p: Parcours) -> str:
    if not p.fiche:
        raise Echec("pas de fiche au geste précédent")
    reponse = p.appeler("GET", f"/v1/fiches/{p.fiche['identifiant']}/export")
    if isinstance(reponse, dict) or "text/html" not in reponse.headers.get("content-type", ""):
        raise Echec("l'export n'est pas une page HTML")
    if CONSTAT not in reponse.text:
        raise Echec("le constat du journaliste n'est pas dans la page exportée")
    return f"page HTML de {len(reponse.text)} caractères, constat en tête"


def verifier_cors(p: Parcours) -> str:
    sondes = {"Origin": p.origine}
    lecture = p.client.get("/v1/etat", headers=sondes)
    if lecture.headers.get("access-control-allow-origin") != p.origine:
        raise Echec(f"GET /v1/etat : origine {p.origine} non autorisée par le service")
    avant_vol = p.client.options(
        "/v1/comparaisons",
        headers={
            **sondes,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": f"{EN_TETE_CLE_DEMO.lower()},content-type",
        },
    )
    autorise = avant_vol.headers.get("access-control-allow-headers", "").lower()
    if avant_vol.status_code != 200 or avant_vol.headers.get("access-control-allow-origin") != p.origine:
        raise Echec(f"pré-vérification refusée (code {avant_vol.status_code})")
    if EN_TETE_CLE_DEMO.lower() not in autorise:
        raise Echec(f"pré-vérification : l'en-tête {EN_TETE_CLE_DEMO} n'est pas autorisé")
    hostile = p.client.get("/v1/etat", headers={"Origin": ORIGINE_HOSTILE})
    if hostile.headers.get("access-control-allow-origin") in ("*", ORIGINE_HOSTILE):
        raise Echec("une origine non déclarée est autorisée")
    return f"origine {p.origine} autorisée (lecture et pré-vérification), une autre origine refusée"


GESTES: list[tuple[str, Callable[[Parcours], str]]] = [
    ("santé", verifier_sante),
    ("radar", verifier_radar),
    ("je cherche", verifier_recherche),
    ("vidéo", verifier_video),
    ("comparaison", verifier_comparaison),
    ("fiche", verifier_fiche),
    ("décision", verifier_decision),
    ("export", verifier_export),
    ("en-tête CORS", verifier_cors),
]


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Vérifie le parcours du journaliste contre un service lancé."
    )
    analyseur.add_argument(
        "--adresse", required=True, help="adresse servie, par exemple http://localhost:8080"
    )
    analyseur.add_argument(
        "--origine", required=True, help="origine des écrans, par exemple http://localhost:5173"
    )
    analyseur.add_argument(
        "--lancer-la-recherche",
        action="store_true",
        help="lancer aussi la recherche en direct (dépense 15 crédits ; sans effet en mode enregistré)",
    )
    arguments = analyseur.parse_args(argv)
    for flux in (sys.stdout, sys.stderr):
        flux.reconfigure(encoding="utf-8")

    cle = os.environ.get("CLE_DEMO", "").strip()
    resultats: list[bool] = []
    with httpx.Client(base_url=arguments.adresse.rstrip("/"), timeout=DELAI_S) as client:
        parcours = Parcours(client, arguments.origine.rstrip("/"), cle)
        parcours.lancer_la_recherche = arguments.lancer_la_recherche
        for nom, geste in GESTES:
            try:
                detail, ok = geste(parcours), True
            except Echec as exc:
                detail, ok = str(exc), False
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                detail, ok = f"réponse inattendue ({type(exc).__name__})", False
            resultats.append(ok)
            print(f"{'OK' if ok else 'KO'}  {nom} : {detail}")
    if not all(resultats):
        print(f"{resultats.count(False)} geste(s) en échec sur {len(resultats)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
