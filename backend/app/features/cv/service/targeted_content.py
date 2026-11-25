"""Composition specific to a CV version generated for a posting."""

from collections.abc import Sequence

from pydantic import Field

from app.agents.tools.cv_compose import Applied, apply_with_report, base_content
from app.agents.tools.cv_lexicon import figures_in
from app.agents.tools.cv_numeric_claims import numeric_claims_supported
from app.agents.tools.cv_schema import CvContent, Link, MasterProfileData, facts_of
from app.agents.tools.cv_validator import cited_facts
from app.agents.tools.posting_schema import PostingAnalysis, contains_term
from app.agents.tools.review_schema import Proposal

# Terms in both languages: a French CV or posting stored earlier still matches.
_AI_TERMS = (
    ("IA", "AI", "intelligence artificielle", "artificial intelligence"),
    ("agent", "agent IA", "agentique", "agentic", "multiagent", "multi agent"),
    ("LLM", "grand modèle de langage", "large language model"),
    ("RAG", "génération augmentée par recherche", "retrieval augmented generation"),
)


class TargetedCvContent(CvContent):
    """The profile links frozen with the version, including those outside the original CV."""

    header_links: list[Link] = Field(default_factory=list)


def _offer_terms(analysis: PostingAnalysis | None) -> tuple[tuple[str, ...], ...]:
    if analysis is None:
        return _AI_TERMS
    aliases = [(keyword.term, *keyword.variants) for keyword in analysis.keywords]
    skills = [*analysis.tools, *(skill.name for skill in analysis.skills)]
    skills += [skill for requirement in analysis.requirements for skill in requirement.skills]
    keywords = {term.casefold() for group in aliases for term in group}
    aliases += [(skill,) for skill in dict.fromkeys(skills) if skill.casefold() not in keywords]
    return (*_AI_TERMS, *aliases)


def _loses_terms(before: str, after: str, terms: tuple[tuple[str, ...], ...]) -> bool:
    return any(
        any(contains_term(before, term, plural=True) for term in group)
        and not any(contains_term(after, term, plural=True) for term in group)
        for group in terms
    )


def _loses_experience(
    proposal: Proposal,
    evidence: dict[str, tuple[str, ...]],
    terms: tuple[tuple[str, ...], ...],
) -> bool:
    if proposal.section != "experience" or proposal.action not in ("remove", "rewrite"):
        return False
    original_lines = evidence.get(proposal.target or "", ())
    after = ""
    if proposal.action == "rewrite":
        after = proposal.after
        # Rewriting a title leaves its achievements in place.
        original_lines = original_lines[:1]
    for before in original_lines:
        if _loses_terms(before, after, terms):
            return True
        original, replacement = figures_in(before), figures_in(after)
        # A corrected figure can be accepted through an impact proposal.
        if original - replacement and (
            proposal.type != "impact" or len(replacement) < len(original)
        ):
            return True
    return False


def _evidence(profile: MasterProfileData) -> dict[str, tuple[str, ...]]:
    evidence: dict[str, tuple[str, ...]] = {
        line.id: (line.text,)
        for experience in profile.experiences
        for line in experience.achievements
    }
    evidence.update(
        (experience.id, (experience.role, *(line.text for line in experience.achievements)))
        for experience in profile.experiences
    )
    return evidence


def compose_targeted_cv(
    base: CvContent,
    profile: MasterProfileData,
    accepted: Sequence[Proposal],
    analysis: PostingAnalysis | None,
    *,
    portfolio: str | None = None,
    latest_profile: MasterProfileData | None = None,
) -> Applied:
    """Keeps the CV's proofs and moves its links into the header of the targeted version."""
    sections = [section for section in base.sections if section.key != "links"]
    present = {section.key for section in sections}
    sections += [
        section
        for section in base_content(profile, ("experience", "skills")).sections
        if section.key not in present
    ]
    evidence, terms = _evidence(profile), _offer_terms(analysis)
    frozen_facts = facts_of(profile)
    current_facts = facts_of(latest_profile) if latest_profile is not None else {}
    kept, ignored = [], []
    for proposal in accepted:
        if (
            proposal.section == "links"
            or _loses_experience(proposal, evidence, terms)
            or not _keeps_numeric_associations(proposal, frozen_facts, current_facts)
        ):
            ignored.append(proposal.ref)
        else:
            kept.append(proposal)
    applied = apply_with_report(base.model_copy(update={"sections": sections}), profile, kept)
    links = list(profile.links)
    if portfolio and all(link.url != portfolio for link in links):
        links.append(Link(label="Portfolio", url=portfolio, sources=["january"]))
    content = TargetedCvContent(**applied.content.model_dump(), header_links=links)
    return Applied(content, [*ignored, *applied.ignored])


def _keeps_numeric_associations(
    proposal: Proposal, frozen: dict[str, str], current: dict[str, str]
) -> bool:
    if proposal.action in ("remove", "move"):
        return True
    # A manual confirmation writes the text into the matching fact of the validated profile.
    confirmed = current.get(proposal.target or "")
    return numeric_claims_supported(proposal.after, cited_facts(proposal, frozen)) or (
        confirmed is not None and numeric_claims_supported(proposal.after, [confirmed])
    )
