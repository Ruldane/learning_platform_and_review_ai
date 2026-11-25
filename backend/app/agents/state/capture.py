"""State of the `capture` flow (D108): the captured source, what the Archivist read from it, the
snapshot of links to the program (references `m3`, `t12` and their ids, F7), the digest, what was
stored and January's answers."""

from typing import Any, TypedDict


class CaptureState(TypedDict, total=False):
    url: str | None
    text: str | None
    document_id: str | None
    source: str  # `url`, `text` or `document` (the original source)
    pasted: bool  # the text comes from the question asked after an unreadable link
    unreadable: bool  # the link could not be read: the text question follows
    material: dict[str, Any]  # `CaptureMaterial` as JSON
    links: dict[str, Any]  # `ProgramLinks` as JSON (ISO dates): the reference snapshot
    digest: dict[str, Any]  # `CaptureDigest` as JSON, unknown references removed
    stored: dict[str, Any]  # `CaptureStored` as JSON
    tick: bool  # January said yes to the covered task
    ticked: bool  # the task is ticked
    want_cards: bool  # January said yes to the cards
    cards_created: int
    outcome: str  # `cancelled`: capture abandoned; empty otherwise
    summary: str
