"""Règles de la partie « revue » du contrôle de la phase 6 (`check_phase6`), en fonctions pures :
chacune lit une réponse de l'API déjà reçue (revue, version, PDF) et lève `CheckFailed` quand une
règle n'est pas tenue. Les messages ne portent que des étapes, des références de modification
(« a1 », « r2 »), des nombres et des noms de champs : jamais un texte du CV, de l'offre ou du
PDF."""

import io
from typing import Any

import pdfplumber

from scripts.phase4_rules import CheckFailed
from scripts.phase6_rules import plain
from scripts.sample_cv import CV_FACTS

MIN_MODIFICATIONS = 3
ATS_CHECKS = (
    "selectable_text",
    "reading_order",
    "standard_headings",
    "contact_in_body",
    "font_sizes",
)
FILENAME_PREFIX = "CV_Camille_Exemple_Societe_Fictive_"
MIN_PDF_TEXT = 150  # caractères lisibles au moins : un CV entier, pas un PDF d'images
EDITED = ("rewrite", "add")  # les actions qui portent un texte `after` adossé à des faits


def has_term(text: str, term: str) -> bool:
    """Le terme figure comme mot (ou suite de mots) entier de `text`, sans accents ni casse."""
    return f" {plain(term)} " in f" {plain(text)} "


def profile_text(data: Any) -> str:
    """Tous les textes du profil validé, mis bout à bout."""
    if isinstance(data, str):
        return data
    items = data.values() if isinstance(data, dict) else data if isinstance(data, list) else []
    return " ".join(profile_text(item) for item in items)


def foreign_terms(review: dict[str, Any], profile: str) -> list[str]:
    """Les termes de l'écart que le profil ne contient nulle part. Le validateur range un terme
    à l'écart quand la ligne qui le cite ne s'appuie sur aucun fait qui le porte ; une autre
    ligne, adossée à un fait qui l'écrit (le résumé dit « agents conversationnels »), peut le
    reprendre sans rien inventer : seul un terme absent de tout le profil ne doit jamais entrer."""
    return [term for term in review["gap_terms"] if not has_term(profile, term)]


def _leaks(mods: list[dict[str, Any]], terms: list[str]) -> list[str]:
    kept = [m for m in mods if m["status"] != "refused"]
    return [m["ref"] for m in kept if any(has_term(m["after"], t) for t in terms)]


def check_proposals(step: str, review: dict[str, Any], profile: str) -> tuple[int, int, int]:
    """Au moins 3 modifications ; chaque modification acceptable d'un clic cite des faits ; aucun
    texte gardé ne contient un terme de l'écart absent du profil. Rend (« à confirmer », termes
    d'écart, dont absents du profil)."""
    mods = review["modifications"]
    if len(mods) < MIN_MODIFICATIONS:
        raise CheckFailed(step, f"{len(mods)} modification(s) : {MIN_MODIFICATIONS} au moins.")
    if review["before"] is None:
        raise CheckFailed(step, "Indicateurs du CV d'origine absents.")
    clear = [m for m in mods if m["status"] == "proposed" and m["action"] in EDITED]
    bare = [m["ref"] for m in clear if not m["fact_ids"]]
    if bare:
        raise CheckFailed(step, f"Modification(s) sans fait cité : {', '.join(bare)}.")
    foreign = foreign_terms(review, profile)
    leaked = _leaks(mods, foreign)
    if leaked:
        raise CheckFailed(step, f"Terme de l'écart dans le texte de : {', '.join(leaked)}.")
    to_confirm = [m for m in mods if m["status"] == "to_confirm"]
    return len(to_confirm), len(review["gap_terms"]), len(foreign)


def check_bulk(step: str, mods: list[dict[str, Any]], result: dict[str, Any]) -> None:
    """Le groupe « accepted » saute exactement les « à confirmer » et accepte tout le reste."""
    held = {m["id"] for m in mods if m["status"] == "to_confirm"}
    if set(result["skipped"]) != held:
        raise CheckFailed(
            step, f"{len(result['skipped'])} sautée(s) : {len(held)} « à confirmer »."
        )
    if result["updated"] != len(mods) - len(held):
        raise CheckFailed(step, f"{result['updated']} acceptée(s) sur {len(mods) - len(held)}.")


def pick_refusal(step: str, mods: list[dict[str, Any]]) -> dict[str, Any]:
    """La modification à refuser : une acceptable si deux le sont (il en reste une), sinon une
    « à confirmer » ; échec s'il n'y en a aucune d'acceptable d'un clic."""
    clear = [m for m in mods if m["status"] != "to_confirm"]
    held = [m for m in mods if m["status"] == "to_confirm"]
    if not clear:
        raise CheckFailed(step, "Aucune modification acceptable d'un clic.")
    return clear[-1] if len(clear) >= 2 or not held else held[0]


def check_decided(
    step: str, review: dict[str, Any], before: list[dict[str, Any]], refused: str, profile: str
) -> None:
    """Après les décisions : la refusée l'est, les autres acceptées gardent leur statut, les
    « à confirmer » restent à confirmer."""
    now = {m["id"]: m for m in review["modifications"]}
    for mod in before:
        want = "refused" if mod["id"] == refused else mod["status"]
        want = "accepted" if want == "proposed" else want
        if now[mod["id"]]["status"] != want:
            raise CheckFailed(step, f"Modification {mod['ref']} : statut inattendu après décision.")
    gaps = _leaks(list(now.values()), foreign_terms(review, profile))
    if gaps:
        raise CheckFailed(step, f"Terme de l'écart dans le texte de : {', '.join(gaps)}.")


def pdf_pages_and_text(step: str, data: bytes) -> tuple[int, str]:
    """Nombre de pages et texte sélectionnable du PDF (pdfplumber) ; `CheckFailed` si illisible."""
    if not data.startswith(b"%PDF"):
        raise CheckFailed(step, "Le fichier téléchargé n'est pas un PDF.")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            texts = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise CheckFailed(step, f"PDF illisible ({type(exc).__name__}).") from None
    return len(texts), "\n".join(texts)


def check_version(
    step: str,
    version: dict[str, Any],
    review: dict[str, Any],
    pdf: bytes,
    disposition: str,
    profile: str,
) -> int:
    """Une version prête : nom de fichier, pages, texte sélectionnable, 5 contrôles ATS verts,
    couverture non réduite, décisions figées au clic, aucun terme de l'écart absent du profil dans
    le texte.
    Rend le nombre de décisions « ignorées » (acceptées que la composition n'a pas placées)."""
    name = version["filename"]
    if not (name.startswith(FILENAME_PREFIX) and name.endswith(".pdf") and name.isascii()):
        raise CheckFailed(step, f"Nom de fichier inattendu (version {version['id']}).")
    if f'filename="{name}"' not in disposition:
        raise CheckFailed(step, "Le téléchargement ne porte pas le nom de fichier de la version.")
    pages, text = pdf_pages_and_text(step, pdf)
    if version["page_count"] != pages or pages != version["original_page_count"]:
        raise CheckFailed(step, f"{pages} page(s) pour {version['original_page_count']} d'origine.")
    if len(plain(text)) < MIN_PDF_TEXT or plain(CV_FACTS["name"]) not in plain(text):
        raise CheckFailed(step, "Texte du PDF non sélectionnable ou incomplet.")
    indicators = version["indicators"]
    if indicators is None:
        raise CheckFailed(step, f"Version {version['id']} sans indicateurs.")
    red = [c["id"] for c in indicators["checks"] if not c["passed"]]
    if red or sorted(c["id"] for c in indicators["checks"]) != sorted(ATS_CHECKS):
        raise CheckFailed(step, f"Contrôles ATS non tenus : {', '.join(red) or 'incomplets'}.")
    if indicators["coverage_percent"] < review["before"]["coverage_percent"]:
        raise CheckFailed(step, "Couverture des exigences plus basse qu'avant la revue.")
    if any(has_term(text, term) for term in foreign_terms(review, profile)):
        raise CheckFailed(step, "Un terme de l'écart figure dans le texte du PDF.")
    return _check_decisions(step, version, review)


def _check_decisions(step: str, version: dict[str, Any], review: dict[str, Any]) -> int:
    ignored = 0
    for mod in review["modifications"]:
        got = version["decisions"].get(mod["ref"])
        if got == "ignored" and mod["status"] == "accepted":
            ignored += 1
        elif got != mod["status"]:
            raise CheckFailed(step, f"Décision de {mod['ref']} différente dans la version.")
    return ignored
