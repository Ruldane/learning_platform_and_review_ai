"""What the Interviewer reads (D145): the posting, the company dossier, the CV version sent, the
known gaps and the profile, each wrapped by `untrusted` (17.4); the interview exchanges
(January's answers included) are too. A missing piece is said to be missing, never invented."""

from app.agents.nodes.tracker.kit_prompt import profile_text
from app.agents.prompts.loader import untrusted
from app.agents.tools.cv_schema import CvContent
from app.agents.tools.interview_schema import Exchange, InterviewContext
from app.agents.tools.kit_schema import CompanyDossier

MAX_POSTING_CHARS = 12_000
NO_POSTING = "No posting is available. Base the interview on the job title."
NO_DOSSIER = "No company dossier is available."
NO_CV = "No CV version is linked to this application."
NO_GAPS = "No known skill gaps."


def posting_block(ctx: InterviewContext) -> str:
    if ctx.posting_text and ctx.posting_text.strip():
        return untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "job posting")
    if ctx.analysis is not None:
        lines = [f"Job title: {ctx.analysis.title}", f"Level: {ctx.analysis.level}"]
        lines += [f"- {item.text}" for item in ctx.analysis.requirements]
        return untrusted("\n".join(lines), "job posting")
    return NO_POSTING


def dossier_lines(dossier: CompanyDossier) -> list[str]:
    lines = [
        f"Business: {dossier.activity}",
        f"Product: {dossier.product}",
        f"Culture: {dossier.culture}",
        f"Hiring process: {dossier.interview_process}",
    ]
    if dossier.stack:
        lines.append("Technologies: " + ", ".join(dossier.stack))
    lines += [f"News: {item.text}" for item in dossier.news]
    lines += [f"Point to verify: {point}" for point in dossier.watch_points]
    return lines


def dossier_block(ctx: InterviewContext) -> str:
    if ctx.dossier is None:
        return NO_DOSSIER
    return untrusted("\n".join(dossier_lines(ctx.dossier)), "company dossier")


def _cv_lines(cv: CvContent) -> list[str]:
    lines = [cv.name, *([cv.headline] if cv.headline else [])]
    for section in cv.sections:
        lines.append(f"## {section.title}")
        for entry in section.entries:
            head = " ".join(part for part in (entry.heading, entry.subheading, entry.dates) if part)
            lines += [head, *(f"- {line.text}" for line in entry.lines)]
        lines += [f"- {line.text}" for line in section.items]
    return lines


def cv_block(ctx: InterviewContext) -> str:
    if ctx.cv_content is None:
        return NO_CV
    return untrusted("\n".join(_cv_lines(ctx.cv_content)), "submitted CV")


def gaps_block(ctx: InterviewContext) -> str:
    if not ctx.gaps:
        return NO_GAPS
    return untrusted("\n".join(f"- {gap}" for gap in ctx.gaps), "known skill gaps")


def profile_block(ctx: InterviewContext) -> str:
    return untrusted(profile_text(ctx.profile), "January's profile")


def exchange_text(
    exchange: Exchange, *, with_note: bool = True, pending_follow_up: bool = False
) -> str:
    """An exchange as the model reads it: the index (from 0), the question, the answers.
    `pending_follow_up`: the follow-up's answer is the one handed over to read, not here yet."""
    lines = [
        f"[index {exchange.index}] Question ({exchange.criterion}): {exchange.question}",
        f"January's answer: {exchange.answer}",
    ]
    if exchange.follow_up:
        lines.append(f"Follow-up: {exchange.follow_up}")
    if exchange.follow_up and not pending_follow_up:
        lines.append(f"Follow-up answer: {exchange.follow_up_answer or '(no answer)'}")
    if with_note:
        note = "unscored (the model did not reply)" if exchange.unrated else f"{exchange.note}/5"
        lines.append(f"Internal score: {note}")
    return "\n".join(lines)


def exchanges_block(exchanges: list[Exchange]) -> str:
    return untrusted("\n\n".join(exchange_text(e) for e in exchanges), "interview exchanges")


MODE_LABELS = {
    "behavioral": "behavioral",
    "technical": "technical",
    "case": "case study",
    "mixed": "mixed (behavioral and technical)",
    "salary": "salary negotiation simulation",
}
MODE_GUIDES = {
    "behavioral": (
        "Behavioral mode: ask about past experience, collaboration, challenges and motivations. "
        "A good answer describes the situation, action and result."
    ),
    "technical": (
        "Technical mode: ask about the tools, concepts and practices the role requires, "
        "from fundamentals to more nuanced topics."
    ),
    "case": (
        "Case study mode: open with a realistic scenario for the role and use later questions "
        "to move it forward. January explains her reasoning in writing."
    ),
    "mixed": (
        "Mixed mode: alternate behavioral and technical questions. "
        "Use roughly equal numbers of each."
    ),
}


def head_vars(ctx: InterviewContext) -> dict[str, object]:
    """The variables at the start of the prompt, common to the Interviewer's three tasks."""
    return {
        "role": untrusted(ctx.role, "job title"),
        "mode_label": MODE_LABELS[ctx.mode],
        "duration": ctx.duration_min,
        "language": ctx.language,
        "salary": ctx.salary is not None,
    }
