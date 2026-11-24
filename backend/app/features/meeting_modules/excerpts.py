import re

from app.features.meeting_modules.schemas import ExcerptKind, MeetingExcerpt, MeetingStudyStep

_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_LABEL = re.compile(
    r"^(décision|decision|choix|à étudier|a etudier|sujet|question|action)\s*:\s*",
    re.IGNORECASE,
)
_DECISIONS = frozenset({"décision", "decision", "choix"})
_DECISION_SENTENCE = re.compile(
    r"^(?:nous\s+avons|on\s+a|il\s+a\s+été|j[’']ai|l[’']équipe\s+a)\s+décidé\b",
    re.IGNORECASE,
)


def extract(transcript: str) -> list[MeetingExcerpt]:
    excerpts: list[MeetingExcerpt] = []
    for index, original in enumerate(transcript.splitlines(), start=1):
        candidate = _MARKER.sub("", original.strip(), count=1)
        label = _LABEL.match(candidate)
        selection = candidate[label.end() :] if label else candidate
        selection = selection.strip()[:600]
        if not selection:
            continue
        is_decision = (
            label.group(1).casefold() in _DECISIONS
            if label
            else _DECISION_SENTENCE.match(candidate) is not None
        )
        kind: ExcerptKind = "decision" if is_decision else "topic"
        excerpts.append(MeetingExcerpt(line=index, kind=kind, text=selection))
        if len(excerpts) >= 60:
            break
    return excerpts


def study_steps(excerpts: list[MeetingExcerpt], selected: list[int]) -> list[MeetingStudyStep]:
    selected_by_line = {item.line: item for item in excerpts}
    return [_study_step(selected_by_line[line]) for line in selected]


def _study_step(item: MeetingExcerpt) -> MeetingStudyStep:
    if item.kind == "decision":
        return MeetingStudyStep(
            source_line=item.line,
            instruction="Restate the decision and compare it with a solution of your choice.",
            criterion=(
                "Give one advantage, one drawback and the context where your choice would change."
            ),
            minutes=8,
        )
    return MeetingStudyStep(
        source_line=item.line,
        instruction="Find a concrete example of this topic and check it on a comparable case.",
        criterion="Name the data that checks your example and explain your result.",
        minutes=10,
    )
