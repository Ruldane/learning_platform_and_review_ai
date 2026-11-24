"""Simulated hiring committee schemas (SPEC F19, D147). A 422 names the fields
(`details.fields`), never their value: the CV and the committee's words are personal data.

`status`: `running` (in progress), `done` (verdict stored), `failed` (the session ended without a
result). `previous`: the before and after, `None` without an older finished run on the same
posting, or while this one is not finished. It is a simulation, never a prediction."""

from datetime import datetime

from pydantic import BaseModel

from app.agents.tools.committee_schema import Persona, Verdict
from app.db.models.applications import RunStatus as RunStatus
from app.features.applications.schemas import Id


class CommitteeIn(BaseModel):
    """The CV version to be judged: it must be ready (PDF rendered)."""

    cv_version_id: Id


class CommitteeStartOut(BaseModel):
    run_id: str
    session_id: str


class VoteOut(BaseModel):
    """A persona's vote: yes, no or maybe, its main objection, its reason."""

    persona: Persona
    vote: Verdict
    objection: str
    reason: str


class ObjectionOut(BaseModel):
    """A committee objection (the heaviest first) and the personas who raise it."""

    text: str
    personas: list[Persona]


class ChangeOut(BaseModel):
    """One of the three changes that would flip a vote: the targeted persona, the profile facts
    to highlight. `needs_skill`: it calls for a term the profile does not state (`terms`), a
    skill "to acquire", never to be written into the CV as is."""

    text: str
    persona: Persona
    fact_ids: list[str]
    needs_skill: bool
    terms: list[str]


class VoteChange(BaseModel):
    """A persona's vote before (previous run) and after (this one)."""

    persona: Persona
    before: Verdict
    after: Verdict


class CommitteeDiff(BaseModel):
    """The before and after (F19): the votes, the objections that disappeared
    (`objections_resolved`) and the new ones (`objections_new`) compared with run `previous_id`."""

    previous_id: str
    votes: list[VoteChange]
    objections_resolved: list[str]
    objections_new: list[str]


class CommitteeRunOut(BaseModel):
    """A committee run. `votes`, `objections` and `changes` are empty until it finishes;
    `verdict` is the majority of the four votes (tie: maybe)."""

    id: str
    cv_version_id: str
    posting_id: str
    application_id: str | None
    session_id: str
    status: RunStatus
    votes: list[VoteOut]
    verdict: Verdict | None
    objections: list[ObjectionOut]
    changes: list[ChangeOut]
    previous: CommitteeDiff | None
    created_at: datetime
