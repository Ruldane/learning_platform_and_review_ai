"""Matériel des tests des revues de CV (D130) : un gabarit prêt et actif (capturé du CV fictif,
polices préparées), un profil validé (`compose_profile`), une offre analysée de « Société
Fictive », les propositions rangées comme par le parcours, la session mise en attente de la
question de sortie, et un faux lanceur qui reprend cette question (`ResumeSpy`) en rendant la
version comme le ferait le parcours. Aucun LLM, aucun réseau, aucun Gotenberg."""

from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_validator import Verdict
from app.agents.tools.review_schema import Proposal
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.career import CvTemplate, MasterProfile
from app.features.cv.service.review_store import AgentCvReviewStore
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates_store import AgentCvTemplateStore
from tests.features.cv.templates_support import capture, liberation_spec
from tests.features.postings.conftest import add_posting
from tests.support.cv_review import compose_profile
from tests.support.cv_template import content as cv_content
from tests.support.gap import analysis_data
from tests.support.text_renderer import TextHtmlRenderer

OUTPUT = {"kind": "cv_output", "question": "Que veux-tu maintenant ?", "options": [], "fields": []}
SECRET_LINE = "Anime une équipe de 8 personnes"  # « à confirmer » : chiffre absent du profil
EDITED = "Réduit les coûts de 30 % avec Python et Docker"
GAP_TEXT = "Déploie sur AWS"


def proposal(ref: str, action: Any, target: str | None, after: str, **kw: Any) -> Proposal:
    section = kw.pop("section", "experience")
    return Proposal(
        ref=ref,
        section=section,
        action=action,
        target=target,
        after=after,
        reason="Plus clair pour l'offre.",
        type=kw.pop("type", "clarity"),
        fact_ids=kw.pop("fact_ids", []),
    )


OK = Verdict("ok", [], [])
ITEMS: list[tuple[Proposal, Verdict]] = [
    (
        proposal("a1", "rewrite", "x1a1", "Réduit les coûts de 30 % avec Python", fact_ids=["c1"]),
        OK,
    ),
    (proposal("a2", "add", "c3", "Kubernetes", section="skills", type="keyword"), OK),
    (
        proposal("r1", "rewrite", "x1a2", SECRET_LINE, type="impact"),
        Verdict("to_confirm", ["Chiffre absent de ton profil"], []),
    ),
    (proposal("r2", "remove", "p1a1", "", section="projects", type="length"), OK),
    (proposal("a3", "add", "c2", GAP_TEXT, section="skills"), Verdict("to_gap", ["x"], ["AWS"])),
]


async def ready_template(rt: CvRuntime, user_id: str) -> str:
    """Un gabarit capturé du CV fictif, polices préparées, prêt et actif (1 page)."""
    template_id = await capture(rt, user_id=user_id)
    await AgentCvTemplateStore(rt).prepare(user_id, template_id)
    async with rt.session_factory() as db:
        row = await db.get(CvTemplate, template_id)
        assert row is not None
        row.status, row.active = "ready", True
        row.spec = liberation_spec().model_dump(mode="json")
        row.sample_content = cv_content().model_dump(mode="json")
        await db.commit()
    return template_id


async def validated_profile(rt: CvRuntime, user_id: str, version: int = 1) -> None:
    async with rt.session_factory() as db:
        db.add(
            MasterProfile(
                user_id=user_id,
                version=version,
                status="validated",
                data=compose_profile().model_dump(mode="json"),
                source="january",
            )
        )
        await db.commit()


async def ready_posting(rt: CvRuntime, user_id: str, **over: Any) -> str:
    fields: dict[str, Any] = {
        "status": "ready",
        "analysis": analysis_data(),
        "company": "Société Fictive",
        "title": "AI Product Engineer (H/F)",
        "url": "https://jobs.example.org/offres/1",
    } | over
    return await add_posting(rt.session_factory, user_id, **fields)


async def set_session(rt: CvRuntime, session_id: str, status: str, pending: Any = None) -> None:
    async with rt.session_factory() as db:
        await db.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id)
            .values(status=status, pending_interrupt=pending)
        )
        await db.commit()


async def wait_output(rt: CvRuntime, session_id: str, interrupt_id: str = "i-1") -> None:
    """La session attend « Que veux-tu maintenant ? »."""
    await set_session(rt, session_id, "waiting_user", {"interrupt_id": interrupt_id, **OUTPUT})


async def propose(rt: CvRuntime, user_id: str, review_id: str, session_id: str) -> None:
    """Les propositions rangées comme par le parcours, puis la question de sortie posée."""
    store = AgentCvReviewStore(rt)
    report = ReviewReport(ats="greenhouse", strengths=["Python"], risks=[])
    await store.save_proposals(user_id, session_id, review_id, ITEMS, ["AWS"], report)
    await wait_output(rt, session_id)


@dataclass
class ResumeSpy:
    """Reprise de la question de sortie comme par le moteur : la session repart (`running`),
    puis, si `render`, la version est rendue par le vrai port et la question revient."""

    rt: CvRuntime
    render: bool = True
    error: AppError | None = None
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    async def resume(self, user_id: str, session_id: str, interrupt_id: str, value: Any) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((session_id, interrupt_id, value))
        await set_session(self.rt, session_id, "running")
        if self.render:
            await AgentCvReviewStore(self.rt).render_version(user_id, value["version_id"])
            await wait_output(self.rt, session_id, f"i-{len(self.calls) + 1}")


def renderer(rt: CvRuntime, *pages: int) -> TextHtmlRenderer:
    """Rendu lisible (texte réel, nombre de pages réglable appel par appel)."""
    text = TextHtmlRenderer(pages=pages or (1,))
    rt.html_pdf = text
    return text


API = "/api/v1"


async def open_review(
    client: httpx.AsyncClient, app: FastAPI, *, proposed: bool = True
) -> tuple[str, str]:
    """Gabarit, profil et offre prêts, revue lancée par la route (lanceur factice), puis, si
    `proposed`, propositions rangées et question de sortie posée ; rend `(revue, session)`."""
    rt: CvRuntime = app.state.career.cv
    me: str = app.state.local_user_id
    await ready_template(rt, me)
    await validated_profile(rt, me)
    posting_id = await ready_posting(rt, me)
    r = await client.post(f"{API}/cv/reviews", json={"posting_id": posting_id})
    assert r.status_code == 202, r.text
    review_id, session_id = r.json()["review_id"], r.json()["session_id"]
    if proposed:
        await propose(rt, me, review_id, session_id)
    return review_id, session_id


async def review(client: httpx.AsyncClient, review_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/cv/reviews/{review_id}")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


async def mods(client: httpx.AsyncClient, review_id: str) -> dict[str, dict[str, Any]]:
    """Les modifications de la revue, par référence."""
    return {m["ref"]: m for m in (await review(client, review_id))["modifications"]}


async def decide(
    client: httpx.AsyncClient, mod_id: str, status: str, **extra: Any
) -> httpx.Response:
    return await client.patch(f"{API}/cv/modifications/{mod_id}", json={"status": status, **extra})


async def post_generate(client: httpx.AsyncClient, review_id: str, **body: Any) -> httpx.Response:
    return await client.post(f"{API}/cv/reviews/{review_id}/generate", json=body)


async def version(client: httpx.AsyncClient, version_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/cv/versions/{version_id}")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body
