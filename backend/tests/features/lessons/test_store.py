"""`AgentLessonStore` (port `LessonStore` sur la feature `lessons`, D91) : fiche du module,
publication (leçon, ressources, PDF, mémoire) idempotente, copie locale des PDF libres sinon
fiche de lecture, échec qui ne touche jamais une leçon prête, filtre utilisateur partout."""

from sqlalchemy import func, select

from app.agents.tools.lesson_port import LessonReport, ResourcePick
from app.core.errors import AppError
from app.db.models.learning import Goal
from app.db.models.lessons import Lesson, Resource
from app.db.models.memory import MemoryItem
from app.db.models.research import Source
from app.features.lessons.service.store import AgentLessonStore
from app.features.program.service.runtime import ProgramRuntime
from app.features.research.service.cache import url_key
from tests.features.lessons.conftest import ME, OTHER, Program, draft_program
from tests.features.program.support import Factory
from tests.support.lessons import lesson_markdown
from tests.support.memory import FakeHtmlRenderer
from tests.support.research import FakeFetcher

SESSION = "11111111-2222-3333-4444-555555555555"
PDF = b"%PDF-1.7 article libre %%EOF"
REPORT = LessonReport(words=1500, unsupported=(), problems=(), revisions=1)


async def add_sources(
    factory: Factory, session_id: str, count: int, *, user_id: str = ME, kept: bool = True
) -> list[Source]:
    rows = []
    async with factory() as db:
        for n in range(count):
            url = f"https://site{n}.exemple.org/article"
            row = Source(
                user_id=user_id,
                session_id=session_id,
                kind="page",
                url=url,
                url_hash=url_key(url),
                title=f"Article {n}",
                author=f"Autrice {n}",
                lang="en" if n % 2 else "fr",
                published=f"2025-0{n + 1}-01",
                status="ok",
                verdict="kept" if kept else "rejected",
                score=80 - n,
                reason="Source sérieuse et récente.",
                summary=f"Résumé de l'article {n}.",
            )
            db.add(row)
            rows.append(row)
        await db.commit()
    return rows


def picks(sources: list[Source]) -> list[ResourcePick]:
    return [
        ResourcePick(
            source_id=s.id,
            type="article",
            duration_minutes=20,
            level="debutant",
            reason="Explique clairement la notion.",
        )
        for s in sources
    ]


async def publish(store: AgentLessonStore, program: Program, sources: list[Source]) -> str:
    done = await store.publish(
        ME,
        SESSION,
        program.modules[0],
        markdown=lesson_markdown(1500),
        resources=picks(sources),
        report=REPORT,
    )
    return done.lesson_id


async def _count(factory: Factory, model: type) -> int:
    async with factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_publish_saves_lesson_pdf_resources_and_memory(
    program_rt: ProgramRuntime,
    store: AgentLessonStore,
    db_session_factory: Factory,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    program = await draft_program(program_rt)
    sources = await add_sources(db_session_factory, SESSION, 4)
    done = await store.publish(
        ME,
        SESSION,
        program.modules[0],
        markdown=lesson_markdown(1500),
        resources=picks(sources),
        report=REPORT,
    )
    assert done.pdf_ok and done.resources == 4
    async with db_session_factory() as db:
        lesson = (await db.execute(select(Lesson))).scalar_one()
        resources = (await db.execute(select(Resource))).scalars().all()
        kinds = (await db.execute(select(MemoryItem.kind))).scalars().all()
    assert lesson.status == "ready" and lesson.pdf_key and lesson.word_count == 1500
    assert lesson.report is not None and lesson.report["revisions"] == 1
    assert len(resources) == 4 and list(kinds) == ["lecon"]
    # Auteur, date et langue viennent de la ligne `sources`, pas du modèle.
    first = next(r for r in resources if r.source_id == sources[0].id)
    assert (first.author, first.published, first.lang) == ("Autrice 0", "2025-01-01", "fr")
    assert (first.type, first.score, first.reason) == ("article", 80, picks(sources)[0].reason)
    assert len(fake_html_renderer.documents) == 1
    # Rejoué (nœud `publish` après un arrêt) : la même leçon, rien de plus.
    again = await publish(store, program, sources)
    assert again == done.lesson_id
    assert await _count(db_session_factory, Resource) == 4
    assert await _count(db_session_factory, MemoryItem) == 1
    assert len(fake_html_renderer.documents) == 1


async def test_free_pdf_is_stored_locally_otherwise_reading_note(
    program_rt: ProgramRuntime,
    store: AgentLessonStore,
    db_session_factory: Factory,
    fetcher: FakeFetcher,
) -> None:
    program = await draft_program(program_rt)
    sources = await add_sources(db_session_factory, SESSION, 3)
    fetcher.files[sources[0].url] = ("application/pdf", PDF)
    await publish(store, program, sources)
    async with db_session_factory() as db:
        rows = {r.source_id: r for r in (await db.execute(select(Resource))).scalars()}
    local = rows[sources[0].id]
    assert local.local_key is not None and local.note is None
    assert await program_rt.memory.providers.storage.read(ME, local.local_key) == PDF
    other = rows[sources[1].id]
    assert other.local_key is None and other.note == "Résumé de l'article 1."
    tried = len(fetcher.calls)
    await publish(store, program, sources)  # rejoué : rien n'est retenté
    assert len(fetcher.calls) == tried


async def test_pdf_failure_keeps_the_lesson_readable(
    program_rt: ProgramRuntime,
    store: AgentLessonStore,
    db_session_factory: Factory,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    fake_html_renderer.failures = 5
    program = await draft_program(program_rt)
    sources = await add_sources(db_session_factory, SESSION, 3)
    done = await store.publish(
        ME,
        SESSION,
        program.modules[0],
        markdown=lesson_markdown(1500),
        resources=picks(sources),
        report=REPORT,
    )
    assert not done.pdf_ok
    fake_html_renderer.failures = 0
    await publish(store, program, sources)  # rejoué : le PDF manquant est rattrapé
    async with db_session_factory() as db:
        lesson = (await db.execute(select(Lesson))).scalar_one()
    assert lesson.status == "ready" and lesson.pdf_key is not None


async def test_resource_picks_must_be_kept_pages_of_the_session(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    kept = await add_sources(db_session_factory, SESSION, 3)
    rejected = await add_sources(db_session_factory, "autre-session", 1, kept=False)
    done = await store.publish(
        ME,
        SESSION,
        program.modules[0],
        markdown=lesson_markdown(1500),
        resources=picks(kept + rejected),
        report=REPORT,
    )
    assert done.resources == 3


async def test_fail_never_touches_a_ready_lesson(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    await store.fail(ME, SESSION, program.modules[1], "x" * 400)
    sources = await add_sources(db_session_factory, SESSION, 3)
    await publish(store, program, sources)
    await store.fail(ME, SESSION, program.modules[0], "Trop tard")
    async with db_session_factory() as db:
        rows = {r.module_id: r for r in (await db.execute(select(Lesson))).scalars()}
    assert rows[program.modules[0]].status == "ready"
    failed = rows[program.modules[1]]
    assert failed.status == "failed" and len(failed.failure_reason or "") == 300


async def test_brief_reads_the_module_and_council_seeds(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    council = "c" * 36
    sources = await add_sources(db_session_factory, council, 7)
    async with db_session_factory() as db:
        goal = await db.get(Goal, program.goal_id)
        assert goal is not None
        goal.council_session_id = council
        source = await db.get(Source, sources[6].id)
        assert source is not None
        source.title = "Module Bases : tout comprendre"  # parle du module : en tête
        await db.commit()
    brief = await store.brief(ME, program.modules[0])
    assert (brief.title, brief.week_rank, brief.week_theme) == ("Module Bases", 1, "Bases")
    assert brief.goal_text == "Devenir data engineer" and brief.language == "fr"
    assert brief.skills == ("pandas",) and brief.program_id == program.program_id
    assert len(brief.seed_urls) == 5 and brief.seed_urls[0] == sources[6].url


async def test_every_call_checks_the_owner(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    module_id = program.modules[0]
    for call in (
        store.brief(OTHER, module_id),
        store.fail(OTHER, SESSION, module_id, "Non"),
        store.publish(OTHER, SESSION, module_id, markdown="# x", resources=[], report=REPORT),
    ):
        try:
            await call
        except AppError as exc:
            assert exc.code == "module_not_found"
        else:  # pragma: no cover
            raise AssertionError("un module d'un autre ne doit jamais être touché")
    assert await _count(db_session_factory, Lesson) == 0
