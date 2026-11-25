"""State of the `study_session` graph (D102). The lesson comes from the port (`StudyContext`, one
read); only the end of the session is written, by the port, in `wrap_up`. The state keeps the
position in the session (phase, rank), the current question and its hints, and the outcome of each
question (`outcomes`)."""

from typing import Any, TypedDict


class StudySessionState(TypedDict, total=False):
    study_session_id: str
    context: dict[str, Any]  # `StudyContext` as JSON (sections and sources as dictionaries)
    memory: str  # Tutor's memory context, already framed by the port
    # Position: `section` (section rank), `exercise` (0), `final` (rank 0...2), `done`
    phase: str
    index: int
    finals: list[dict[str, str]]  # {question, expected}: the 3 final questions, written once
    question: str  # current question (asked by `ask`)
    expected: str  # its expected answer (the lesson's model answer for the exercise)
    hints: int  # hints given for the current question
    given_hints: list[str]  # their text, to grade the next one
    reply: dict[str, Any] | None  # `TutorAnswer` as JSON; None: unreadable answer
    outcomes: list[dict[str, Any]]  # `Outcome` as JSON, in order
    last_input_seq: int  # dernier `user.message` lu
    board_step: int  # last step number of the Tutor's board
    ended_early: bool  # "End" before the last question
    session_summary: str  # Tutor's summary (`SessionSummary`)
    finished: dict[str, Any]  # `StudyFinished` as JSON
    summary: str  # `run.completed` summary
