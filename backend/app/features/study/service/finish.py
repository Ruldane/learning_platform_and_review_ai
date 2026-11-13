"""Fin d'une session guidée (SPEC F14, D103), rangée en UNE transaction, sous le verrou du
programme pris AVANT elle (F4), gardée par `UPDATE … SET status = 'finished' WHERE status =
'open'` : rejouée (nœud `wrap_up` relancé après un arrêt), elle relit ce qui est rangé et n'écrit
rien de plus ; une session abandonnée entre-temps rend une fin vide, sans rien écrire.

Ce qu'elle écrit : le temps (`worked_minutes` gardé par la route, déjà borné par la durée réelle ;
0 s'il manque), les tâches du bloc cochées (`lire` et `regarder` si January n'a pas terminé avant
la fin, `pratiquer` si l'exercice est fait, F13), les compétences du module montées à `en_cours`
au plus (jamais `valide` : seuls un quiz ou un projet valident, 4.5) avec une preuve `study`,
et seulement si la séance laisse une trace (au moins une minute ou une réponse à une question :
une fin rangée par la route sans minuteur ni réponse ne monte rien, D103 n° 18), une
fiche par question manquée (`partial`, `wrong`, `revealed` ; jamais `skipped`), le bilan et une
ligne de journal `study_session` (« study:{id} »). Les niveaux changés sont reflétés dans la
mémoire après le commit, hors du verrou, et rattrapés au rejeu (comme le quiz). Journaux :
identifiants et nombres seulement."""

import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.study_port import StudyFinished, StudyOutcome
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.program import Module
from app.db.models.skills import SkillLevel
from app.db.models.study import StudySession
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.program.service.followup import tick_tasks
from app.features.program.service.programs import load
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.skills.service import SkillsService
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.service.runtime import StudyRuntime

logger = logging.getLogger(__name__)

READING = ("lire", "regarder")
PRACTICE = ("pratiquer",)
CARD_VERDICTS = ("partial", "wrong", "revealed")  # « Passer » ne crée pas de fiche (D103)
CEILING: SkillLevel = "en_cours"  # jamais au-delà (4.5)
EMPTY = StudyFinished(minutes=0, tasks_done=[], flashcards_created=0, skills=[])


def study_not_found() -> AppError:
    return AppError("study_session_not_found", "Session d'étude introuvable.", 404)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count > 1 else ''}"


def journal_text(module: str, minutes: int, tasks: int, cards: int) -> str:
    ticked = f"{_plural(tasks, 'tâche')} cochée{'s' if tasks > 1 else ''}"
    return f"Session « {module} » : {minutes} min, {ticked}, {_plural(cards, 'fiche')}."


def finished_of(row: StudySession) -> StudyFinished:
    """La fin déjà rangée (rejeu), ou une fin vide pour une session abandonnée."""
    if row.status != "finished":
        return EMPTY
    result: dict[str, Any] = (row.outcome or {}).get("result", {})
    skills = [(str(name), level) for name, level in result.get("skills", [])]
    return StudyFinished(
        minutes=row.minutes,
        tasks_done=[str(t) for t in result.get("tasks_done", [])],
        flashcards_created=int(result.get("flashcards_created", 0)),
        skills=skills,
    )


def _ticked_types(outcome: StudyOutcome) -> tuple[str, ...]:
    return (() if outcome.ended_early else READING) + (PRACTICE if outcome.exercise_done else ())


def _cards(row: StudySession, outcome: StudyOutcome) -> list[NewCard]:
    return [
        NewCard(o.question, o.expected, None, row.module_id, "study", row.id)
        for o in outcome.outcomes
        if o.verdict in CARD_VERDICTS and o.expected.strip()
    ]


async def _module(db: AsyncSession, row: StudySession) -> Module | None:
    loaded = await load(db, row.user_id, row.program_id)
    return next((m for m in loaded.modules if m.id == row.module_id), None)


async def _title(db: AsyncSession, row: StudySession, module: Module | None) -> str:
    if module is not None:
        return module.title
    return (await StudyReadRepository(db, row.user_id).titles(row.lesson_id, ""))[0]


def _has_trace(minutes: int, outcome: StudyOutcome) -> bool:
    """Au moins une minute de travail ou une réponse à une question (D103 n° 18)."""
    return minutes > 0 or bool(outcome.outcomes)


async def _write(
    rt: StudyRuntime, db: AsyncSession, row: StudySession, outcome: StudyOutcome, now: datetime
) -> tuple[StudyFinished, str]:
    """Range la fin (la session vient d'être réclamée `finished`) ; ne commite pas."""
    user_id, today = row.user_id, await rt.today(db, row.user_id)
    reads = StudyReadRepository(db, user_id)
    module = await _module(db, row)
    title = await _title(db, row, module)
    minutes = row.worked_minutes or 0
    wanted = _ticked_types(outcome)
    block = [str(t) for t in row.task_ids]
    types = {t.id: t.type for t in await reads.tasks(block)}
    ids = [t for t in block if types.get(t) in wanted]  # dans l'ordre du bloc
    done = await tick_tasks(db, rt.program, user_id, ids)
    skills = [str(s) for s in module.skills] if module and _has_trace(minutes, outcome) else []
    label = f"Session guidée « {title} » ({today:%d/%m})"
    changed = await SkillsService(db, user_id).raise_levels(
        skills, CEILING, evidence("study", row.id, label, now)
    )
    cards = await add_cards(db, user_id, _cards(row, outcome), today)
    result = StudyFinished(minutes, done, cards, changed)
    row.minutes, row.summary = minutes, outcome.summary.strip() or None
    row.outcome = {"outcome": asdict(outcome), "result": asdict(result)}
    await db.flush()
    await _journal(db, row, title, result, today)
    return result, title


async def _journal(
    db: AsyncSession, row: StudySession, title: str, result: StudyFinished, today: date
) -> None:
    await add_entry(
        db,
        row.user_id,
        kind="study_session",
        text=journal_text(title, result.minutes, len(result.tasks_done), result.flashcards_created),
        occurred_on=today,
        ref_key=f"study:{row.id}",
        links=JournalLinks(session_id=row.session_id, study_session_id=row.id),
        data={"lesson_id": row.lesson_id, "minutes": result.minutes, "summary": row.summary},
    )


async def _claim_and_write(
    rt: StudyRuntime, user_id: str, study_id: str, outcome: StudyOutcome
) -> tuple[StudyFinished, bool, str]:
    async with rt.session_factory() as db:
        repo = StudyRepository(db, user_id)
        now = rt.now()
        claimed = await repo.close_open(study_id, status="finished", ended_at=now)
        row = await repo.get_fresh(study_id)
        if row is None:
            raise study_not_found()
        if not claimed:
            done = finished_of(row)
            # Le titre ne sert qu'au reflet rattrapé (rien à refléter : pas de lecture de plus).
            return done, False, await _title(db, row, await _module(db, row)) if done.skills else ""
        result, title = await _write(rt, db, row, outcome, now)
        await db.commit()
    return result, True, title


async def finish_study(
    rt: StudyRuntime, user_id: str, session_id: str | None, study_id: str, outcome: StudyOutcome
) -> StudyFinished:
    """La fin rangée une seule fois (voir le module) ; 404 pour la session d'une autre.
    `session_id` : la session d'agents qui la range (`None` : la route, session déjà morte)."""
    async with rt.session_factory() as db:
        row = await StudyRepository(db, user_id).get_fresh(study_id)
        if row is None:
            raise study_not_found()
        program_id = row.program_id
    # F4 : le verrou du programme AVANT la transaction d'écriture (même ordre qu'`editing`).
    async with rt.program.program_lock(user_id, program_id):
        result, written, title = await _claim_and_write(rt, user_id, study_id, outcome)
    if result.skills:  # au rejeu aussi : reflet idempotent, jamais baissé (rattrape un arrêt)
        try:
            await reflect_skill_levels(
                rt.memory,
                user_id,
                result.skills,
                author="tutor",
                session_id=session_id,
                reason=f"Session guidée « {title} »",
            )
        except Exception:
            logger.warning("Acquis non reflétés après une session guidée : étude %s", study_id)
    if written:
        logger.info(
            "Session guidée rangée : étude %s, %d min, %d tâche(s), %d fiche(s), %d acquis",
            study_id,
            result.minutes,
            len(result.tasks_done),
            result.flashcards_created,
            len(result.skills),
        )
    return result
