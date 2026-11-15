"""Ré-import (I-D, D137 n° 1) : le fait de January qui remplace un brouillon équivalent prend les
dates, le lieu et l'URL que le nouveau CV renseigne ; ce que le brouillon ne dit pas reste à
January."""

from typing import Any

from app.agents.tools.cv_schema import (
    Education,
    Experience,
    Identity,
    MasterProfileData,
    Project,
    assign_fact_ids,
)
from app.features.cv.service.profile_merge import all_ids, merge_draft


def _bare(**kw: Any) -> MasterProfileData:
    return MasterProfileData(identity=Identity(name="Camille Exemple"), **kw)


def _merge(previous: MasterProfileData, draft: MasterProfileData) -> MasterProfileData:
    previous = assign_fact_ids(previous)
    return merge_draft(draft, previous, all_ids([previous]))


def _replaced_job(**draft_over: Any) -> Experience:
    """Le fait de January (« Lead Développeuse », sans fin) remplace le brouillon équivalent
    (« Développeuse », mêmes mots dans le texte de January) ; rend l'expérience fusionnée."""
    previous = _bare(
        experiences=[
            Experience(
                role="Lead Développeuse",
                company="Société Fictive",
                start="2023-01",
                sources=["cv", "january"],
            )
        ]
    )
    draft = _bare(
        experiences=[Experience(role="Développeuse", company="Société Fictive", **draft_over)]
    )
    merged = _merge(previous, draft)
    assert [x.role for x in merged.experiences] == ["Lead Développeuse"]
    assert "january" in merged.experiences[0].sources
    return merged.experiences[0]


def test_replacement_keeps_draft_dates_place_url() -> None:
    job = _replaced_job(start="2023-01", end="2025-06", location="Lyon")
    assert (job.start, job.end, job.location) == ("2023-01", "2025-06", "Lyon")


def test_replacement_keeps_january_value_when_draft_has_none() -> None:
    job = _replaced_job(end="2025-06")  # le brouillon n'a ni début ni lieu
    assert (job.start, job.end, job.location) == ("2023-01", "2025-06", None)


def test_replacement_takes_new_project_url() -> None:
    """Un projet n'a pas de clé lâche : le même nom l'apparie, le brouillon (URL du nouveau CV)
    l'emporte, sous l'id de l'ancien."""
    previous = _bare(
        projects=[Project(name="Tremplin", link="https://example.org/ancien", sources=["january"])]
    )
    draft = _bare(projects=[Project(name="Tremplin", link="https://example.org/nouveau")])
    merged = _merge(previous, draft)
    assert [(p.id, p.link) for p in merged.projects] == [("p1", "https://example.org/nouveau")]


def test_replacement_takes_the_draft_end_of_a_school() -> None:
    previous = _bare(
        education=[
            Education(
                degree="Licence informatique", school="Université Exemple", sources=["january"]
            )
        ]
    )
    draft = _bare(
        education=[
            Education(degree="Licence", school="Université Exemple", start="2018-09", end="2021-06")
        ]
    )
    merged = _merge(previous, draft)
    assert [(e.degree, e.start, e.end) for e in merged.education] == [
        ("Licence informatique", "2018-09", "2021-06")
    ]
