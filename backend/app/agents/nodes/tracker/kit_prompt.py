"""Build kit prompts from the profile, posting, application and style guide (D142, SPEC 17.4)."""

from app.agents.prompts.loader import untrusted
from app.agents.tools.cv_schema import Education, Experience, MasterProfileData, facts_of
from app.agents.tools.kit_schema import KitContext

MAX_POSTING_CHARS = 30_000
NO_CRITERIA = "The analysis found no screening criteria. Read the posting again."
NO_STYLE = "No style guide. Write in plain language and use short sentences."


def profile_text(profile: MasterProfileData) -> str:
    """List the name and facts by ID, including dates for experience and education."""
    dated: list[Experience | Education] = [*profile.experiences, *profile.education]
    periods = {
        item.id: f" ({item.start or '?'} → {item.end or 'present'})"
        for item in dated
        if item.start or item.end
    }
    lines = [f"Name: {profile.identity.name}"]
    lines += [f"[{fact}] {text}{periods.get(fact, '')}" for fact, text in facts_of(profile).items()]
    return "\n".join(lines)


def card_text(ctx: KitContext) -> str:
    lines = [f"Company: {ctx.company}", f"Exact job title: {ctx.title}"]
    if ctx.contact:
        lines.append(f"Contact: {ctx.contact}")
    return "\n".join(lines)


def _eliminatory(ctx: KitContext) -> str:
    """Return the posting's screening criteria as untrusted data."""
    texts = [item.text for item in ctx.analysis.eliminatory]
    return untrusted("\n".join(texts), "screening criteria") if texts else NO_CRITERIA


def prompt_vars(ctx: KitContext, style_guide: str) -> dict[str, object]:
    return {
        "card": untrusted(card_text(ctx), "application"),
        "profile": untrusted(profile_text(ctx.profile), "January's profile"),
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "posting"),
        "style_guide": untrusted(style_guide, "style guide") if style_guide.strip() else NO_STYLE,
        "eliminatory": _eliminatory(ctx),
    }
