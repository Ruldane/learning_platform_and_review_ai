"""State of the `lesson_factory` graph (D90). It inherits the Scout's state: its nodes
join the graph as they are, node for node (same keys, same checkpoints as
`web_research`). The lesson itself is written to the database only on publication (port
`LessonStore`): the state keeps the draft, its checks and the chosen resources."""

from typing import Any

from app.agents.state.web_research import WebResearchState


class LessonFactoryState(WebResearchState, total=False):
    program_id: str
    module_id: str
    verification: bool  # direct submission linked to the session
    citation_urls: list[str]  # order of the addresses in the submitted draft
    brief: dict[str, Any]  # `ModuleBrief` as JSON
    resources: list[dict[str, Any]]  # `ResourcePick` as JSON: 3 to 6, fewer if the web gives none
    resource_notes: list[str]  # minor remarks (insufficient resources)
    draft: str  # Writer's Markdown
    revisions: int  # revisions already requested from the Writer (0: first version)
    words: int  # draft words, code blocks excluded
    problems: list[str]  # deterministic checks not met (French sentences)
    check_categories: list[str]  # public categories, without an extract of the draft
    unsupported: list[str]  # unsourced claims flagged by the Verifier
    scores: dict[str, int]  # teaching scores out of 100, per criterion
    best: dict[str, Any]  # best checked version, its rank and its checks (D305)
    published: dict[str, Any]  # `PublishedLesson` as JSON
    failure: str  # reason the lesson failed
    next_module: str | None  # module whose lesson the chain has just started
