"""Carte de compétences (SPEC F15, D107) : graphe et radar, détail d'une compétence (preuves,
offres, prochaine action).

Hors de `service` : la carte lit les services `program`, `lessons` et `quiz`, et
`program.service` importe `skills.service` (un import dans l'autre sens ferait un cycle).
Tout est relu à chaque requête, sans cache : `user_skills` fait foi (D6) et un changement de
niveau se voit à la lecture suivante (« moins d'une minute »)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.core.skills import Evidence, EvidenceKind, read_evidence
from app.db.models.skills import Skill, SkillLevel
from app.features.lessons.service.lessons import ready_lesson_id
from app.features.program.service.skill_modules import module_teaching
from app.features.quiz.service.cards import due_skill_names
from app.features.quiz.service.quizzes import ready_quiz_of_module
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
    SkillDetailOut,
    SkillEdgeOut,
    SkillGraphOut,
    SkillNodeOut,
)

STUDY_URL = "/etudier/session"
QUIZ_URL = "/etudier/quiz"
REVIEW_URL = "/etudier/revisions"
JOURNAL_URL = "/etudier/journal"
# Page de chaque genre de preuve qui désigne un objet (`ref_id`) ; « capture » mène au journal.
_EVIDENCE_PAGES: dict[EvidenceKind, str] = {
    "lesson": "/apprendre/lecons/",
    "quiz": "/etudier/quiz/",
    "study": "/etudier/session/",
    "program": "/apprendre/programme/",
}


def skill_not_found() -> AppError:
    return AppError("skill_not_found", "Compétence introuvable.", 404)


async def skill_graph(db: AsyncSession, user_id: str) -> SkillGraphOut:
    """Toutes les compétences de January (triées par nom), leurs prérequis et le radar."""
    skills = await SkillRepository(db, user_id).list_all()
    rows = await UserSkillRepository(db, user_id).rows()
    levels = {skill_id: as_level(row.level) for skill_id, row in rows.items()}
    nodes = [
        SkillNodeOut(
            id=skill.id,
            name=skill.name,
            domain=domain_name(skill.domain),
            level=levels.get(skill.id),
            demand=None,  # Radar du marché (F12) en phase 8
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
    """Le chemin de la preuve dans l'application, `None` si elle n'a pas de page (projet, CV,
    preuve de la phase 4 sans référence)."""
    if item["kind"] == "capture":
        return JOURNAL_URL
    page = _EVIDENCE_PAGES.get(item["kind"])
    ref_id = item["ref_id"]
    return f"{page}{quote(ref_id, safe='')}" if page is not None and ref_id else None


def _instant(value: str) -> datetime | None:
    """L'instant ISO d'une preuve ; `None` s'il est vide (phase 4) ou illisible."""
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
    """Ce que la prochaine action a besoin de savoir, lu selon le niveau seulement."""

    module: str | None = None  # titre du module qui enseigne la compétence
    lesson_id: str | None = None  # leçon prête de ce module
    quiz_id: str | None = None  # quiz prêt de ce module
    cards_due: bool = False  # une fiche de la compétence est due aujourd'hui


def next_action(level: SkillLevel | None, skill: str, facts: ActionFacts) -> NextActionOut | None:
    """La prochaine action selon le niveau (D107 n° 5) : absente ou déclarée → étudier ; en
    cours → passer le quiz ; validée → réviser ses fiches dues, sinon le projet preuve (bientôt) ;
    prouvée → rien. Sans module qui l'enseigne, le libellé nomme la compétence."""
    subject = facts.module or skill
    if level is None or level == "declare":
        url = f"{STUDY_URL}?lecon={quote(facts.lesson_id, safe='')}" if facts.lesson_id else None
        return NextActionOut(kind="study", label=f"Étudier « {subject} »", url=url or STUDY_URL)
    if level == "en_cours":
        url = f"{QUIZ_URL}/{quote(facts.quiz_id, safe='')}" if facts.quiz_id else QUIZ_URL
        return NextActionOut(kind="quiz", label=f"Passer le quiz « {subject} »", url=url)
    if level == "valide":
        if facts.cards_due:
            label = f"Réviser les fiches « {skill} »"
            return NextActionOut(kind="review", label=label, url=REVIEW_URL)
        return NextActionOut(kind="project", label="Projet preuve (bientôt)", url=None)
    return None


async def _facts(
    db: AsyncSession, user_id: str, skill: Skill, level: SkillLevel | None, now: datetime
) -> ActionFacts:
    if level == "prouve":
        return ActionFacts()
    if level == "valide":
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        due = await due_skill_names(db, user_id, local_today(zone, now))
        return ActionFacts(cards_due=skill.norm_name in due)
    module = await module_teaching(db, user_id, skill.norm_name)
    if module is None:
        return ActionFacts()
    if level == "en_cours":
        quiz_id = await ready_quiz_of_module(db, user_id, module.module_id)
        return ActionFacts(module=module.title, quiz_id=quiz_id)
    lesson_id = await ready_lesson_id(db, user_id, module.module_id)
    return ActionFacts(module=module.title, lesson_id=lesson_id)


async def skill_detail(
    db: AsyncSession, user_id: str, skill_id: str, now: datetime
) -> SkillDetailOut:
    """Une compétence de January : preuves (la plus récente d'abord), offres (vides jusqu'à la
    phase 6) et prochaine action ; 404 `skill_not_found` si elle n'est pas à elle."""
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
        postings=[],  # offres en phase 6
        next_action=next_action(level, skill.name, facts),
    )
