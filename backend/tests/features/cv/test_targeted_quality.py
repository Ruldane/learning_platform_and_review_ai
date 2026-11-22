"""Du CV synthétique actualisé au vrai téléchargement, avec un rendu local factice."""

import re

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_schema import (
    Experience,
    Identity,
    Line,
    Link,
    MasterProfileData,
    SkillFact,
    assign_fact_ids,
)
from app.agents.tools.template_schema import ColumnSpec
from app.db.models.career import CvTemplate, MasterProfile
from app.features.cv.service.templates_store import AgentCvTemplateStore
from scripts.sample_pdf import make_pdf
from tests.features.cv.reviews_support import (
    API,
    OK,
    ResumeSpy,
    decide,
    mods,
    proposal,
    ready_posting,
    wait_output,
)
from tests.features.cv.templates_support import capture, liberation_spec
from tests.features.cv.test_generate import generate, pdf_text, rt_of
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.text_renderer import TextHtmlRenderer

_LINKS = [
    ("Site personnel", "https://camille.example.org", "cv"),
    ("LinkedIn", "https://linkedin.example.org/camille", "linkedin"),
    ("Code", "https://code.example.org/camille", "note"),
]
_AGENTS = "Déployé des agents IA de support avec LangGraph."
_RESULTS = "Réduit le délai de résolution de 37 % en production."
_LOW_VALUE = "Participation aux réunions hebdomadaires."
_SKILLS = ["Python", "LangGraph", "Docker", "RAG", "SQL", "Qdrant"]


def _profile() -> MasterProfileData:
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            experiences=[
                Experience(
                    company="Studio Fictif",
                    role="Ingénieure IA",
                    achievements=[Line(text=line) for line in (_AGENTS, _RESULTS, _LOW_VALUE)],
                    sources=["cv"],
                )
            ],
            skills=[SkillFact(name=skill, sources=["cv"]) for skill in _SKILLS],
            links=[Link(label=label, url=url, sources=[source]) for label, url, source in _LINKS],
        )
    )


async def _review(client: httpx.AsyncClient, app: FastAPI, wide: bool) -> tuple[str, str]:
    rt = rt_of(app)
    me: str = app.state.local_user_id
    pdf = make_pdf(
        ["Camille Exemple", _LINKS[0][1], "Ingénieure IA", _AGENTS, _RESULTS, _LOW_VALUE, *_SKILLS]
    )
    source = await rt.layout.extract_layout(pdf)
    assert all(text in source.pages[0].stream_text for text in (_LINKS[0][1], _AGENTS, _RESULTS))
    template_id = await capture(rt, pdf=pdf, user_id=me)
    await AgentCvTemplateStore(rt).prepare(me, template_id)
    spec = liberation_spec()
    main = ColumnSpec(width_pct=68, sections=["identity", "experience"])
    sidebar = ColumnSpec(width_pct=32, sections=["links"])
    (main if wide else sidebar).sections.append("skills")
    spec.columns = [main, sidebar]
    async with rt.session_factory() as db:
        row = await db.get(CvTemplate, template_id)
        assert row is not None
        row.status, row.active, row.spec = "ready", True, spec.model_dump(mode="json")
        db.add(
            MasterProfile(
                user_id=me,
                version=1,
                status="validated",
                data=_profile().model_dump(),
                source="january",
            )
        )
        await db.commit()
    posting_id = await ready_posting(rt, me)
    response = await client.post(f"{API}/cv/reviews", json={"posting_id": posting_id})
    assert response.status_code == 202, response.text
    return response.json()["review_id"], response.json()["session_id"]


async def test_generated_header_retains_all_profile_links(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await _review(client, app, wide=True)
    await app.state.career.cv_review.save_proposals(
        app.state.local_user_id, session_id, review_id, [], [], ReviewReport()
    )
    await wait_output(rt_of(app), session_id)
    version = await generate(client, review_id)
    html = fake_renderer.documents[-1].index_html
    header = html.split('<section class="identity">', 1)[1].split("</section>", 1)[0]
    pdf = await pdf_text(app, client, version["id"])
    for label, url, _ in _LINKS:
        assert f'href="{url}"' in header and label in header
        assert html.count(f'href="{url}"') == 1
        assert url in pdf


async def test_targeted_generation_trims_only_lower_value_experience_details(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
) -> None:
    review_id, session_id = await _review(client, app, wide=True)
    cuts = [
        proposal("r1", "rewrite", "x1a1", "Déployé un outil de support.", type="length"),
        proposal("r2", "remove", "x1a2", "", type="length"),
        proposal("r3", "remove", "x1a3", "", type="length"),
    ]
    await app.state.career.cv_review.save_proposals(
        app.state.local_user_id,
        session_id,
        review_id,
        [(cut, OK) for cut in cuts],
        [],
        ReviewReport(),
    )
    await wait_output(rt_of(app), session_id)
    for row in (await mods(client, review_id)).values():
        assert (await decide(client, row["id"], "accepted")).status_code == 200
    version = await generate(client, review_id)
    pdf = " ".join((await pdf_text(app, client, version["id"])).split())
    assert _AGENTS in pdf and _RESULTS in pdf
    assert _LOW_VALUE not in pdf
    assert version["decisions"] == {"r1": "ignored", "r2": "ignored", "r3": "accepted"}


@pytest.mark.parametrize(("wide", "columns"), [(False, 2), (True, 3)])
async def test_generated_skills_use_available_template_width(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
    wide: bool,
    columns: int,
) -> None:
    review_id, session_id = await _review(client, app, wide=wide)
    await app.state.career.cv_review.save_proposals(
        app.state.local_user_id, session_id, review_id, [], [], ReviewReport()
    )
    await wait_output(rt_of(app), session_id)
    version = await generate(client, review_id)
    html = fake_renderer.documents[-1].index_html
    section = html.split('class="cv-section section-skills">', 1)[1].split("</section>", 1)[0]
    assert f"items skills-columns-{columns}" in section
    assert re.findall(r'<li class="line">([^<]+)</li>', section) == _SKILLS
    pdf = await pdf_text(app, client, version["id"])
    assert all(skill in pdf for skill in _SKILLS)
