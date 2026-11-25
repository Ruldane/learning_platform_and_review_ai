"""State of the `cv_capture` graph (D124, D125). The profile, its sources and the CV content are
personal data: the state keeps them for the session's duration (checkpoints), never a log.
Page images are **never** in the state (reread through the port by each node that
shows them to the layout designer): each checkpoint stays light."""

from typing import Any, TypedDict


class CvCaptureState(TypedDict, total=False):
    mode: str  # "profile" | "design"
    document_ids: list[str]
    note: str | None
    template_id: str | None
    # Mode `profile` (Archiviste)
    sources: list[dict[str, str]]  # `ProfileSource` as JSON: {kind, text}
    hidden: list[str]  # hidden lines of PDFs (preflight G6)
    draft: dict[str, Any]  # `MasterProfileData` as JSON, provisional ids then checked
    dropped: list[str]  # text of the lines and facts removed, shown to January only
    unsupported: int  # lines removed: figure not found
    untraced: int  # facts removed: not found in the documents
    version: int  # number of the stored draft
    summary: str
    # Mode `design` (Maquettiste)
    selectable: bool  # false: scanned CV
    page_count: int
    sample: dict[str, Any]  # `CvContent` as JSON: demonstration content
    spec: dict[str, Any]  # `TemplateSpec` as JSON: current description
    pass_no: int  # last pass rendered (1 to 3 automatic, then one per adjustment)
    score: int  # score of the last pass
    kept_pass: int  # pass kept by the port (`keeps_pass`): the best, D125
    kept_score: int  # score of the kept pass: the one January validates
    kept_spec: dict[str, Any]  # description of the kept pass: "Adjust" restarts from it
    stalled: bool  # the last correction did not give a valid description
    adjustments: int  # adjustments requested by January (5 at most)
    instruction: str | None  # last instruction from January (500 characters at most)
    answer: dict[str, Any] | None  # parsed answer to the `cv_template` question
