"""Vues du défi et de sa note, sans fichiers remis ni résultat brut du bac."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.agents.tools.boss_port import BossGrade

BossState = Literal["building", "expired", "reviewing", "graded", "review_failed"]


class BossClientChange(BaseModel):
    at: datetime
    requirement: str


class BossAttemptOut(BaseModel):
    id: str
    ide_session_id: str
    state: BossState
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None
    server_time: datetime
    brief: str
    client_change: BossClientChange | None
    grade: BossGrade | None
    proof_recorded: bool


class BossProgramOut(BaseModel):
    program_id: str
    title: str
    eligible: bool
    attempt: BossAttemptOut | None


class BossReviewStarted(BaseModel):
    session_id: str
