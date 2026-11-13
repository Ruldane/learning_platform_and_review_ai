"""Partie pure de l'Analyste (D121) : variables des prompts (offre et référentiel encadrés comme
non fiables), règles de l'analyse renvoyées au modèle, nettoyage de l'analyse et des
rattachements, textes annoncés. Aucune entrée-sortie ici."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.agents.prompts.loader import untrusted
from app.agents.tools.gap_port import (
    MAX_KNOWN_SKILLS,
    AnalysisSaved,
    DuplicateHit,
    GapSaved,
    SkillMatch,
    SkillMatches,
)
from app.agents.tools.posting_schema import (
    PostingAnalysis,
    contains_term,
    keyword_problems,
    requirement_problems,
)
from app.core.skills import normalize_skill_name

AGENT = "analyst"
# Dernière phrase de chaque demande : les modèles scriptés des tests s'y reconnaissent.
ANALYZE_REQUEST = "Analyse cette offre."
MATCH_REQUEST = "Rattache ces besoins au référentiel de January."
NOT_A_POSTING = "Ce texte ne ressemble pas à une offre d'emploi : aucune analyse n'est lancée."
MAX_ANALYZE_ASKS = 3  # une demande + deux re-demandes avec les problèmes de l'analyse
MAX_POSTING_CHARS = 30_000  # texte de l'offre montré à l'Analyste
_LEVEL_ORDER = {"certain": 0, "probable": 1, "possible": 2}


# --- Mode `analyze` -----------------------------------------------------------------------------


def analyze_vars(text: str) -> dict[str, Any]:
    """Variables du mode `analyze` d'`analyst.md` : l'offre est un contenu non fiable (17.4)."""
    return {"mode": "analyze", "posting": untrusted(text[:MAX_POSTING_CHARS], "offre")}


def analysis_problems(analysis: PostingAnalysis, text: str) -> list[str]:
    """Ce qui est renvoyé au modèle : mots clés absents de l'offre (formulation exacte, D121
    n° 2), exigences obligatoires sans compétence. Un texte qui n'est pas une offre n'a pas de
    problème : il est refusé tel quel."""
    if not analysis.is_job_posting:
        return []
    return keyword_problems(analysis, text) + requirement_problems(analysis)


def problems_text(problems: list[str]) -> str:
    return (
        "Ton analyse ne respecte pas les règles :\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\nCorrige-la et rends de nouveau l'analyse complète."
    )


def drop_absent_keywords(analysis: PostingAnalysis, text: str) -> tuple[PostingAnalysis, int]:
    """L'analyse sans les mots clés qui ne figurent toujours pas tels quels dans l'offre, et leur
    nombre (journalisé, jamais les termes)."""
    kept = [k for k in analysis.keywords if contains_term(text, k.term)]
    dropped = len(analysis.keywords) - len(kept)
    return analysis.model_copy(update={"keywords": kept}), dropped


# --- Mode `match` -------------------------------------------------------------------------------


def _need_line(name: str, required: bool) -> str:
    return f"- {' '.join(name.split())} ({'obligatoire' if required else 'souhaitée'})"


def match_vars(analysis: PostingAnalysis, known: Sequence[str]) -> dict[str, Any]:
    """Variables du mode `match` : les besoins viennent de l'offre, les noms du référentiel de
    January ; les deux sont encadrés comme non fiables."""
    needs = "\n".join(_need_line(s.name, s.required) for s in analysis.skills)
    names = "\n".join(f"- {' '.join(n.split())}" for n in known[:MAX_KNOWN_SKILLS])
    return {
        "mode": "match",
        "needs": untrusted(needs, "offre:competences"),
        "known": untrusted(names or "Aucune compétence.", "referentiel"),
    }


def clean_matches(
    analysis: PostingAnalysis, found: SkillMatches | None, known: Sequence[str]
) -> tuple[list[SkillMatch], int]:
    """Un rattachement par besoin de l'analyse (dans son ordre, sans doublon de nom). Le nom
    rendu par le modèle n'est gardé que s'il est dans le référentiel (écrit comme lui) ; sinon
    `None`, jamais inventé (D121 n° 3). Un besoin laissé sans rattachement dont le nom figure tel
    quel au référentiel lui est rattaché. Rend aussi le nombre de noms hors référentiel."""
    by_key = {normalize_skill_name(name): name for name in known[:MAX_KNOWN_SKILLS]}
    answers: dict[str, str | None] = {}
    for item in found.items if found is not None else []:
        answers.setdefault(normalize_skill_name(item.need), item.known)
    unknown = sum(
        1 for name in answers.values() if name and normalize_skill_name(name) not in by_key
    )
    matches: list[SkillMatch] = []
    seen: set[str] = set()
    for need in analysis.skills:
        key = normalize_skill_name(need.name)
        if key in seen:
            continue
        seen.add(key)
        answer = answers.get(key)
        name = by_key.get(normalize_skill_name(answer)) if answer else None
        matches.append(SkillMatch(need=need.name, known=name or by_key.get(key)))
    return matches, unknown


# --- Instantanés en JSON (état du graphe) -------------------------------------------------------


def duplicates_json(saved: AnalysisSaved) -> list[dict[str, Any]]:
    return [asdict(hit) for hit in saved.duplicates]


def saved_json(saved: GapSaved) -> dict[str, Any]:
    return asdict(saved)


# --- Textes annoncés ----------------------------------------------------------------------------


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count > 1 else ''}"


def gap_text(saved: GapSaved) -> str:
    """« Score de match : 62/100. 4 compétences manquent, dont 2 obligatoires. »"""
    head = f"Score de match : {saved.score}/100."
    if saved.missing == 0:
        return f"{head} Aucune compétence ne manque."
    verb = "manquent" if saved.missing > 1 else "manque"
    text = f"{head} {_plural(saved.missing, 'compétence')} {verb}"
    if saved.missing_required:
        text += f", dont {_plural(saved.missing_required, 'obligatoire')}"
    return f"{text}."


def duplicate_text(duplicates: Sequence[dict[str, Any]]) -> str | None:
    """« Offre proche d'une offre déjà ajoutée le 03/11. » : le doublon le plus sûr, puis le plus
    ancien ; `None` sans doublon. La date est celle de l'ajout (UTC)."""
    hits = [DuplicateHit(**hit) for hit in duplicates]
    if not hits:
        return None
    first = min(hits, key=lambda hit: (_LEVEL_ORDER[hit.level], hit.created_at))
    day = datetime.fromisoformat(first.created_at).strftime("%d/%m")
    return f"Offre proche d'une offre déjà ajoutée le {day}."
