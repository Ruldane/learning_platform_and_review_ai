"""Schémas des projets preuves (P1 à P4, D165) : l'énoncé écrit par le Praticien, son évaluation et
les quatre brouillons au nom de January. Rien ici ne décide d'un fait : le verdict, les longueurs
et la référence d'honnêteté sont du code.

- `verdict` : « validé » seulement si **chaque** critère de 1 à N a **un seul** résultat et que tous
  sont atteints ; un résultat manquant, en double ou d'un rang hors de 1 à N fait « à reprendre ».
  `settled_results` range un résultat par critère (un critère sans résultat unique n'est pas
  atteint) pour le port et pour la phrase de fin.
- `project_fact` / `project_reference` (P4) : le fait de projet (titre de l'énoncé, description de
  January, compétences du module) ajouté au profil validé (ou à une identité vide). Le README du
  dépôt n'y entre jamais : c'est du texte web, pas un fait de January. La description (4 000
  caractères au plus) est coupée en lignes de 600 caractères au plus, la taille d'un fait du
  profil : `text_claims` la lit en entier.
- `draft_text` : le texte que `text_claims` contrôle, pour chaque brouillon.

Les lignes écrites par le modèle (critères, contraintes, nom et réalisations de l'entrée de profil)
sont ramenées à **une seule ligne** (`one_line`) avant toute vérification : un retour à la ligne ne
fabrique jamais un faux critère numéroté, et une valeur blanche est refusée (nouvel essai) au lieu
d'être rangée puis refusée à la lecture. Les textes lus par January sont raccourcis (`Prose`,
`ShortenToMax`) plutôt que refusés (D97) ; les plafonds en mots du plan sont posés en caractères
(7,5 par mot) dans le schéma envoyé au modèle ; seul le post LinkedIn est compté en mots, par le
code (`linkedin_words`)."""

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import (
    Identity,
    Line,
    MasterProfileData,
    Project,
    SkillFact,
    assign_fact_ids,
)
from app.db.models.daily import DraftKind, DraftStatus

__all__ = [
    "DRAFT_KINDS",
    "LINKEDIN_WORDS",
    "NOT_ASSESSED",
    "CriterionResult",
    "DraftKind",
    "DraftStatus",
    "ProfileEntryDraft",
    "ProjectBrief",
    "ProjectDrafts",
    "ProjectEvaluation",
    "draft_text",
    "linkedin_words",
    "project_fact",
    "project_reference",
    "settled_results",
    "unmet_count",
    "verdict",
]

DRAFT_KINDS: tuple[DraftKind, ...] = ("cv_line", "profile_entry", "linkedin_post", "readme_plan")
LINKEDIN_WORDS = (80, 200)  # mots du post LinkedIn, comptés par le code
NOT_ASSESSED = "Critère non évalué."
_LINE = 600  # taille d'une ligne de fait du profil (`Line.text`)
_DESCRIPTION = 4_800  # 8 lignes de 600 : la description de 4 000 caractères tient en entier
_MAX_LINES = 8  # `Project.achievements`


def one_line(value: object) -> object:
    """Le texte sur une seule ligne : blancs et retours à la ligne ramenés à une espace."""
    return " ".join(value.split()) if isinstance(value, str) else value


def _stripped(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


Short = Annotated[
    str, Field(min_length=1, max_length=160), ShortenToMax(), BeforeValidator(one_line)
]
Criterion = Annotated[
    str, Field(min_length=1, max_length=200), ShortenToMax(), BeforeValidator(one_line)
]
Achievement = Annotated[
    str, Field(min_length=1, max_length=200), ShortenToMax(), BeforeValidator(one_line)
]
PlanStep = Annotated[str, Field(min_length=1, max_length=120), ShortenToMax()]


class ProjectBrief(BaseModel):
    """L'énoncé d'un mini projet : 3 à 6 critères qu'un relecteur peut vérifier, 3 à 6 heures."""

    title: str = Field(min_length=3, max_length=120)
    context: Prose = Field(min_length=1, max_length=900)  # 120 mots au plus
    objective: Prose = Field(min_length=1, max_length=450)  # 60 mots au plus
    constraints: list[Short] = Field(min_length=2, max_length=5)
    criteria: list[Criterion] = Field(min_length=3, max_length=6)
    hours: int = Field(ge=3, le=6)
    deliverable: Literal["repo", "description", "either"]


class CriterionResult(BaseModel):
    index: int = Field(ge=1)  # rang du critère, à partir de 1
    met: bool
    comment: Prose = Field(default="", max_length=300)


class ProjectEvaluation(BaseModel):
    results: list[CriterionResult] = Field(max_length=6)
    feedback: Prose = Field(min_length=1, max_length=1500)  # 200 mots au plus


class ProfileEntryDraft(BaseModel):
    """L'entrée de projet que January peut ajouter à son profil (jamais sans son clic)."""

    name: Annotated[str, Field(min_length=1, max_length=120), BeforeValidator(one_line)]
    description: Annotated[
        str, Field(max_length=600), ShortenToMax(), BeforeValidator(_stripped)
    ] = ""
    achievements: list[Achievement] = Field(default_factory=list, max_length=4)


class ProjectDrafts(BaseModel):
    cv_line: Annotated[str, Field(min_length=1, max_length=200), ShortenToMax()]
    profile_entry: ProfileEntryDraft
    linkedin_post: Prose = Field(
        min_length=1, max_length=1800
    )  # 80 à 200 mots, comptés par le code
    readme_plan: list[PlanStep] = Field(min_length=5, max_length=10)


def linkedin_words(text: str) -> int:
    return len(text.split())


def _by_index(results: Sequence[CriterionResult]) -> dict[int, list[CriterionResult]]:
    found: dict[int, list[CriterionResult]] = {}
    for result in results:
        found.setdefault(result.index, []).append(result)
    return found


def verdict(
    criteria_count: int, results: Sequence[CriterionResult]
) -> Literal["validated", "to_redo"]:
    """« validé » : un résultat par critère de 1 à N, tous atteints, aucun rang hors de 1 à N."""
    found = _by_index(results)
    if criteria_count < 1 or any(not 1 <= index <= criteria_count for index in found):
        return "to_redo"
    complete = all(
        len(found.get(index, [])) == 1 and found[index][0].met
        for index in range(1, criteria_count + 1)
    )
    return "validated" if complete else "to_redo"


def settled_results(
    criteria_count: int, results: Sequence[CriterionResult]
) -> list[CriterionResult]:
    """Un résultat par critère de 1 à N, dans l'ordre : celui du modèle s'il est unique, sinon
    « non évalué » (manquant ou en double) ; un rang hors de 1 à N est écarté."""
    found = _by_index(results)
    return [
        found[index][0]
        if len(found.get(index, [])) == 1
        else CriterionResult(index=index, met=False, comment=NOT_ASSESSED)
        for index in range(1, criteria_count + 1)
    ]


def unmet_count(criteria_count: int, results: Sequence[CriterionResult]) -> int:
    """Les critères non atteints ou sans résultat unique, sur N."""
    return sum(not result.met for result in settled_results(criteria_count, results))


def draft_text(kind: DraftKind, drafts: ProjectDrafts) -> str:
    """Le texte de chaque brouillon, tel que `text_claims` le contrôle."""
    if kind == "cv_line":
        return drafts.cv_line
    if kind == "linkedin_post":
        return drafts.linkedin_post
    if kind == "readme_plan":
        return "\n".join(drafts.readme_plan)
    entry = drafts.profile_entry
    return "\n".join([entry.name, entry.description, *entry.achievements]).strip()


def _chunks(text: str, size: int) -> list[str]:
    """`text` en morceaux de `size` caractères au plus, coupés entre deux mots."""
    chunks: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > size:  # un « mot » plus long qu'une ligne : coupé net
            if current:
                chunks.append(current)
                current = ""
            chunks.append(word[:size])
            word = word[size:]
        if current and len(current) + 1 + len(word) > size:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


def project_fact(
    title: str, description: str | None, skills: Sequence[str], repo_url: str | None
) -> Project:
    """Le fait de projet : le titre de l'énoncé, ce que January en dit (en lignes de 600
    caractères au plus), puis les compétences du module. Sans identifiant (`project_reference`)."""
    pieces = _chunks((description or "")[:_DESCRIPTION], _LINE)
    names = [name for name in dict.fromkeys(skills) if name.strip()]
    lines = [Line(text=piece) for piece in pieces[1 : _MAX_LINES + 1]]
    if names and len(lines) < _MAX_LINES:
        lines.append(Line(text=f"Compétences : {', '.join(names)}"[:_LINE]))
    return Project(
        name=title[:120],
        description=pieces[0] if pieces else "",
        link=repo_url[:300] if repo_url else None,
        achievements=lines,
        sources=["january"],
    )


def project_reference(
    profile: MasterProfileData | None, fact: Project, skills: Sequence[str]
) -> MasterProfileData:
    """Ce que les brouillons ont le droit de dire : le profil validé (ou une identité vide), le
    fait de projet et les compétences du module. Les identifiants sont attribués par le code."""
    base = profile or MasterProfileData(identity=Identity(name="January"))
    extra = [
        SkillFact(name=name[:80], sources=["january"])
        for name in dict.fromkeys(skills)
        if name.strip()
    ]
    merged = base.model_copy(
        update={"projects": [*base.projects, fact], "skills": [*base.skills, *extra]}
    )
    return assign_fact_ids(merged)
