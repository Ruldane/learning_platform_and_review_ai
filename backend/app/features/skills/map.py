"""Skill map (SPEC F15, D107, D123): graph and radar, detail of a skill (evidence, offers that cite
it, next action).

Outside `service`: the map reads the `program`, `lessons` and `quiz` services, and
`program.service` imports `skills.service` (an import the other way would make a cycle).
Everything is re-read on each request, without cache: `user_skills` is authoritative (D6), and a
change of level shows on the next read ("less than a minute")."""

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.core.skills import Evidence, EvidenceKind, normalize_skill_name, read_evidence
from app.db.models.skills import Skill, SkillLevel
from app.features.gap.service.links import postings_citing
from app.features.lessons.service.lessons import ready_lesson_id
from app.features.program.service.skill_modules import module_teaching
from app.features.quiz.service.cards import due_skill_names
from app.features.quiz.service.quizzes import ready_quiz_of_module
from app.features.radar.service.demand import latest_demand
from app.features.settings.service import SettingsService
from app.features.skills.radar import as_level, domain_name, domain_scores
from app.features.skills.repository import (
    SkillEdgeRepository,
    SkillRepository,
    UserSkillRepository,
)
from app.features.skills.schemas import (
    DomainScoreOut,
    EvidenceOut,
    NextActionOut,
    PostingRefOut,
    SkillDetailOut,
    SkillEdgeOut,
    SkillGraphOut,
    SkillNodeOut,
)

STUDY_URL = "/study/session"
QUIZ_URL = "/study/quiz"
REVIEW_URL = "/study/reviews"
JOURNAL_URL = "/study/journal"
POSTING_PAGE = "/career/postings/"
# page for each kind of proof that designates an object (`ref_id`); "capture" leads to the journal
_EVIDENCE_PAGES: dict[EvidenceKind, str] = {
    "lesson": "/learn/lessons/",
    "quiz": "/study/quiz/",
    "study": "/study/session/",
    "program": "/learn/programs/",
    "github": "/skills/portfolio/",
    "system_design": "/applications/system-design/",
    "contribution": "/skills/contributions/",
    "feynman": "/study/explain/",
}


def skill_not_found() -> AppError:
    return AppError("skill_not_found", "Skill not found.", 404)


def _demand(demand: dict[str, float], skill: Skill) -> float | None:
    """The share of the last scan's offers that cite the skill (its name or a synonym, the
    strongest), 0 if the scan does not cite it; `None` without a finished scan."""
    if not demand:
        return None
    names = [skill.norm_name, *(normalize_skill_name(str(s)) for s in skill.synonyms)]
    return max((demand.get(name, 0.0) for name in names), default=0.0)


async def skill_graph(db: AsyncSession, user_id: str) -> SkillGraphOut:
    """All of January's skills (sorted by name), their prerequisites and the radar."""
    skills = await SkillRepository(db, user_id).list_all()
    rows = await UserSkillRepository(db, user_id).rows()
    levels = {skill_id: as_level(row.level) for skill_id, row in rows.items()}
    demand = await latest_demand(db, user_id)
    nodes = [
        SkillNodeOut(
            id=skill.id,
            name=skill.name,
            domain=domain_name(skill.domain),
            level=levels.get(skill.id),
            demand=_demand(demand, skill),
            evidence_count=len(read_evidence(rows[skill.id].evidence)) if skill.id in rows else 0,
        )
        for skill in skills
    ]
    nodes.sort(key=lambda node: (node.name.casefold(), node.id))
    edges = await SkillEdgeRepository(db, user_id).pairs()
    radar = domain_scores([(skill.domain, levels.get(skill.id)) for skill in skills])
    return SkillGraphOut(
        nodes=nodes,
        edges=[SkillEdgeOut(before_id=before, after_id=after) for before, after in edges],
        domains=[DomainScoreOut(domain=domain, score=score) for domain, score in radar],
    )


def evidence_url(item: Evidence) -> str | None:
    """The path of the proof in the application, `None` if it has no page (project, CV, phase 4
    proof without a reference)."""
    if item["kind"] == "capture":
        return JOURNAL_URL
    page = _EVIDENCE_PAGES.get(item["kind"])
    ref_id = item["ref_id"]
    if item["kind"] == "github" and ref_id:
        ref_id = ref_id.partition(":")[0]
    return f"{page}{quote(ref_id, safe='')}" if page is not None and ref_id else None


def _instant(value: str) -> datetime | None:
    """The ISO instant of a proof; `None` if it is empty (phase 4) or unreadable."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _evidence_out(item: Evidence) -> EvidenceOut:
    return EvidenceOut(
        kind=item["kind"], label=item["label"], at=_instant(item["at"]), url=evidence_url(item)
    )


@dataclass(frozen=True)
class ActionFacts:
    """What the next action needs to know, read according to the level only."""

    module: str | None = None  # title of the module that teaches the skill
    lesson_id: str | None = None  # ready lesson of this module
    quiz_id: str | None = None  # ready quiz of this module
    cards_due: bool = False  # a card of the skill is due today


def next_action(level: SkillLevel | None, skill: str, facts: ActionFacts) -> NextActionOut | None:
    """The next action by level (D107 #5): absent or declared → study; in progress → take the quiz;
    validated → review its due cards, otherwise the proof project (coming soon); proven → nothing.
    Without a module that teaches it, the label names the skill."""
    subject = facts.module or skill
    if level is None or level == "declared":
        url = f"{STUDY_URL}?lesson={quote(facts.lesson_id, safe='')}" if facts.lesson_id else None
        return NextActionOut(kind="study", label=f"Study “{subject}”", url=url or STUDY_URL)
    if level == "in_progress":
        url = f"{QUIZ_URL}/{quote(facts.quiz_id, safe='')}" if facts.quiz_id else QUIZ_URL
        return NextActionOut(kind="quiz", label=f"Take the quiz on “{subject}”", url=url)
    if level == "validated":
        if facts.cards_due:
            label = f"Review cards for “{skill}”"
            return NextActionOut(kind="review", label=label, url=REVIEW_URL)
        return NextActionOut(kind="project", label="Evidence project (coming soon)", url=None)
    return None


async def _facts(
    db: AsyncSession, user_id: str, skill: Skill, level: SkillLevel | None, now: datetime
) -> ActionFacts:
    if level == "proven":
        return ActionFacts()
    if level == "validated":
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        due = await due_skill_names(db, user_id, local_today(zone, now))
        return ActionFacts(cards_due=skill.norm_name in due)
    module = await module_teaching(db, user_id, skill.norm_name)
    if module is None:
        return ActionFacts()
    if level == "in_progress":
        quiz_id = await ready_quiz_of_module(db, user_id, module.module_id)
        return ActionFacts(module=module.title, quiz_id=quiz_id)
    lesson_id = await ready_lesson_id(db, user_id, module.module_id)
    return ActionFacts(module=module.title, lesson_id=lesson_id)


async def _postings(db: AsyncSession, user_id: str, skill: Skill) -> list[PostingRefOut]:
    """The ready offers that cite the skill or a synonym (D123)."""
    names = [skill.name, *(str(synonym) for synonym in skill.synonyms)]
    return [
        PostingRefOut(
            id=ref.posting_id,
            title=ref.title,
            url=f"{POSTING_PAGE}{quote(ref.posting_id, safe='')}",
        )
        for ref in await postings_citing(db, user_id, names)
    ]


async def skill_detail(
    db: AsyncSession, user_id: str, skill_id: str, now: datetime
) -> SkillDetailOut:
    """One of January's skills: proofs (most recent first), offers that cite it (10 at most, most
    recent first) and next action; 404 `skill_not_found` if it is not January's."""
    skill = await SkillRepository(db, user_id).get(skill_id)
    if skill is None:
        raise skill_not_found()
    row = (await UserSkillRepository(db, user_id).for_skills([skill.id])).get(skill.id)
    level = as_level(row.level) if row is not None else None
    proofs = read_evidence(row.evidence) if row is not None else []
    facts = await _facts(db, user_id, skill, level, now)
    return SkillDetailOut(
        id=skill.id,
        name=skill.name,
        domain=domain_name(skill.domain),
        synonyms=[str(synonym) for synonym in skill.synonyms],
        level=level,
        evidence=[_evidence_out(item) for item in reversed(proofs)],
        postings=await _postings(db, user_id, skill),
        next_action=next_action(level, skill.name, facts),
    )
