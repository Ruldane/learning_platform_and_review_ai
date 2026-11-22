from pydantic import BaseModel

from app.agents.tools.system_design_port import SystemDesignReview
from app.db.models.applications import InterviewStatus
from app.features.learning.service.design_boards import BoardOut


class DesignSubject(BaseModel):
    title: str
    situation: str
    requirements: tuple[str, ...]


class DesignState(BaseModel):
    id: str
    session_id: str
    status: InterviewStatus
    subject: DesignSubject
    board: BoardOut
    version_id: str | None
    defense: str | None
    review: SystemDesignReview | None
    proof_saved: bool
