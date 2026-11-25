"""Check facts, length, and screening answers in kit pieces (SPEC 1, 18.3, F16, D142).

Facts must come from the profile. The full company name, job title, and contact name
are allowed verbatim. Each section follows its own word limits. Salary expectations
and answers without supporting facts are left blank.

The model gets one retry with details. The user reviews any issues that remain.
"""

from dataclasses import dataclass

from app.agents.tools.kit_schema import Draft, FormAnswer, FormAnswers, KitContext
from app.agents.tools.salary import is_salary_question
from app.agents.tools.text_claims import text_claims

RETRY = (
    "Remove terms unsupported by the profile: {terms}. Rewrite the piece using only "
    "facts from January's profile."
)
LENGTH_RETRY = "Follow the word limits. {problems}"


def allowed_phrases(ctx: KitContext) -> list[str]:
    """Return the full company name, title, and contact name the draft may cite."""
    return [phrase for phrase in (ctx.company, ctx.title, ctx.contact) if phrase]


def flagged_terms(draft: Draft, ctx: KitContext) -> list[str]:
    """List each unsupported term once, in order of appearance."""
    allowed = allowed_phrases(ctx)
    terms: list[str] = []
    for text in draft.parts().values():
        for claim in text_claims(text, ctx.profile, allowed=allowed):
            if claim.term not in terms:
                terms.append(claim.term)
    return terms


def word_counts(draft: Draft) -> dict[str, int]:
    """Count whitespace-separated words in each part that has a limit."""
    parts = draft.parts()
    return {name: len(parts[name].split()) for name in draft.limits}


def meta_words(draft: Draft) -> int | dict[str, int] | None:
    """Return a total for one bounded part or individual counts for multiple parts."""
    counts = word_counts(draft)
    if not counts:
        return None
    return next(iter(counts.values())) if len(counts) == 1 else counts


def _bounds(low: int, high: int) -> str:
    return f"{low} to {high} words" if low > 1 else f"at most {high} words"


def length_problems(draft: Draft) -> list[str]:
    counts = word_counts(draft)
    return [
        f"The `{name}` field has {counts[name]} words. Use {_bounds(low, high)}."
        for name, (low, high) in draft.limits.items()
        if not low <= counts[name] <= high
    ]


@dataclass(frozen=True)
class Review:
    terms: list[str]
    problems: list[str]

    def __bool__(self) -> bool:
        return bool(self.terms or self.problems)


def review(draft: Draft, ctx: KitContext) -> Review:
    return Review(flagged_terms(draft, ctx), length_problems(draft))


def retry_message(found: Review) -> str:
    """Report unsupported terms and out-of-range word counts for the retry."""
    parts = []
    if found.terms:
        parts.append(RETRY.format(terms=", ".join(found.terms)))
    if found.problems:
        parts.append(LENGTH_RETRY.format(problems=" ".join(found.problems)))
    return "\n".join(parts)


def fix_answers(draft: FormAnswers, fact_ids: set[str]) -> FormAnswers:
    """Clear salary answers and unsupported answers and retain only valid fact IDs."""
    items = []
    for item in draft.items:
        valid = [fact for fact in dict.fromkeys(item.fact_ids) if fact in fact_ids]
        if is_salary_question(item.question) or not valid:
            items.append(FormAnswer(question=item.question, answer="", fact_ids=[]))
        else:
            items.append(FormAnswer(question=item.question, answer=item.answer, fact_ids=valid))
    return FormAnswers(items=items)
