"""State of the `application_intake` flow (D141). The record reaches the database only after
January confirms: the state keeps the sentence (the input), the parsed draft, the duplicate alerts,
the answer to the question and the id of the created record."""

from typing import Any, TypedDict


class ApplicationIntakeState(TypedDict, total=False):
    text: str  # January's sentence: never logged (17.2)
    today: str  # January's day (ISO 8601)
    language: str  # her interface language
    draft: dict[str, Any]  # `IntakeDraft` as JSON
    alerts: list[dict[str, Any]]  # `AlertView` as JSON, strongest first
    answer: dict[str, Any] | None  # parsed answer: `{choice, draft}`; `None`: question asked again
    application_id: str  # the record created (`create`, `distinct`) or opened (`open`)
    info: list[dict[str, Any]]  # `InfoView` as JSON: "same company" at creation
    summary: str
