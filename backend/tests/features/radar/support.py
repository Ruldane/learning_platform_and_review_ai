"""Matériel des tests du radar (D160) : un `RadarRuntime` sur la vraie base de test, le vrai port
(`AgentRadarStore`), une recherche web réelle sur un faux lecteur, un lanceur qui écrit la session
`running` sans faire tourner de graphe. Aucun réseau ni LLM. Données fictives (`example.org`)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.agents.tools.radar_schema import RadarFinding
from app.db.models.accounts import User
from app.db.models.agents import AgentSession
from app.db.models.daily import RadarRun
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.providers.web.base import WebDocument
from tests.features.program.support import Factory
from tests.support.memory import FakeWebReader
from tests.support.onboarding import finish_first_launch

ME, OTHER = "moi", "autre"
NOW = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)  # lundi, 9 h à Paris
ROLE, ZONE = "Ingénieur IA", "Lyon"
HOST = "jobs.example.org"


def link(number: int, host: str = HOST) -> str:
    return f"https://{host}/offres/{number}"


def doc(
    url: str, text: str = "Offre fictive : Python, Docker et RAG. 45 000 euros."
) -> WebDocument:
    return WebDocument(url, "Titre", text, None, None, "fr", None)


def finding(ref: str, *skills: str, **over: Any) -> RadarFinding:
    data: dict[str, Any] = {
        "ref": ref,
        "is_job_posting": True,
        "title": f"Poste {ref}",
        "company": "Société Fictive",
        "level": "mid_level",
        "skills": [{"name": name, "required": True} for name in skills],
        "tools": [],
    }
    return RadarFinding.model_validate(data | over)


@dataclass
class Radar:
    """Le radar de test : runtime, port, faux web."""

    rt: RadarRuntime
    store: AgentRadarStore
    web: FakeWebReader
    factory: Factory

    async def new_run(
        self,
        user: str = ME,
        *,
        role: str = ROLE,
        zone: str = ZONE,
        status: str = "running",
        session_id: str | None = None,
        created_at: datetime | None = None,
    ) -> str:
        async with self.factory() as db:
            row = await RadarRunRepository(db, user).add(
                role=role,
                zone=zone,
                role_norm=role.casefold(),
                zone_norm=zone.casefold(),
                trigger="manual",
                status=status,
                session_id=session_id,
                **({"created_at": created_at} if created_at else {}),
            )
            await db.commit()
            return row.id

    async def read(self, run_id: str, count: int, *, start: int = 0, user: str = ME) -> None:
        """Lit `count` pages lisibles (liens `link(start…)`)."""
        for number in range(start, start + count):
            self.web.pages[link(number)] = doc(link(number))
            await self.store.read_posting(user, "s", run_id, link(number))

    async def extract(
        self, run_id: str, skills: list[list[str]], *, start: int = 1, user: str = ME
    ) -> None:
        """Range une offre analysée par liste de compétences, sous les repères `p<start>`…"""
        items = [finding(f"p{start + n}", *names) for n, names in enumerate(skills)]
        await self.store.save_extraction(user, "s", run_id, items, [])

    async def analyzed_run(
        self, skills: list[list[str]], *, user: str = ME, role: str = ROLE, zone: str = ZONE
    ) -> str:
        """Un relevé dont `skills` sont les offres lues et analysées, puis fini."""
        run_id = await self.new_run(user, role=role, zone=zone)
        await self.read(run_id, len(skills), user=user)
        await self.extract(run_id, skills, user=user)
        await self.store.finalize(user, "s", run_id)
        return run_id

    async def row(self, run_id: str) -> RadarRun:
        async with self.factory() as db:
            stmt = select(RadarRun).where(RadarRun.id == run_id)
            return (await db.execute(stmt)).scalar_one()

    async def open_run(self, user: str = ME, **over: Any) -> str:
        """Un relevé `running` avec sa session ouverte (sujet `radar_run`), comme au lancement."""
        run_id = await self.new_run(user, **over)
        async with self.factory() as db:
            session = AgentSession(
                user_id=user,
                graph="market_radar",
                status="running",
                input={"run_id": run_id},
                subject_type="radar_run",
                subject_id=run_id,
            )
            db.add(session)
            await db.flush()
            row = await RadarRunRepository(db, user).get_fresh(run_id)
            assert row is not None
            row.session_id = session.id
            await db.commit()
        return run_id


async def add_users(factory: Factory, *ids: str, onboarded: bool = True) -> None:
    """Des comptes ; par défaut leur premier lancement est fini (le planificateur les traite)."""
    async with factory() as db:
        db.add_all([User(id=one, user_id=one) for one in ids])
        await db.commit()
    if onboarded:
        await finish_first_launch(factory, *ids)
