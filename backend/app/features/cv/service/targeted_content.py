"""Composition propre à la version d'un CV générée pour une offre."""

from collections.abc import Sequence

from pydantic import Field

from app.agents.tools.cv_compose import Applied, apply_with_report, base_content
from app.agents.tools.cv_lexicon import figures_in
from app.agents.tools.cv_schema import CvContent, Link, MasterProfileData
from app.agents.tools.posting_schema import PostingAnalysis, contains_term
from app.agents.tools.review_schema import Proposal

_AI_TERMS = (
    ("IA", "AI", "intelligence artificielle", "artificial intelligence"),
    ("agent", "agent IA", "agentique", "agentic", "multiagent", "multi agent"),
    ("LLM", "grand modèle de langage", "large language model"),
    ("RAG", "génération augmentée par recherche", "retrieval augmented generation"),
)


class TargetedCvContent(CvContent):
    """Les liens du profil figés avec la version, y compris ceux hors du CV d'origine."""

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
        # La réécriture d'un intitulé laisse ses réalisations en place.
        original_lines = original_lines[:1]
    for before in original_lines:
        if _loses_terms(before, after, terms):
            return True
        original, replacement = figures_in(before), figures_in(after)
        # Un chiffre corrigé peut être accepté via une proposition d'impact.
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
) -> Applied:
    """Garde les preuves du CV et déplace ses liens dans l'en-tête de la version ciblée."""
    sections = [section for section in base.sections if section.key != "links"]
    present = {section.key for section in sections}
    sections += [
        section
        for section in base_content(profile, ("experience", "skills")).sections
        if section.key not in present
    ]
    evidence, terms = _evidence(profile), _offer_terms(analysis)
    kept, ignored = [], []
    for proposal in accepted:
        if proposal.section == "links" or _loses_experience(proposal, evidence, terms):
            ignored.append(proposal.ref)
        else:
            kept.append(proposal)
    applied = apply_with_report(base.model_copy(update={"sections": sections}), profile, kept)
    content = TargetedCvContent(**applied.content.model_dump(), header_links=profile.links)
    return Applied(content, [*ignored, *applied.ignored])
