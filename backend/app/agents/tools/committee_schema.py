"""Schemas of the simulated hiring committee (SPEC F19, D147): the four personas, their vote, the
Moderator's synthesis and the context that the `hiring_committee` graph reads.

What the code decides, the model does not choose: the verdict is the majority of the four votes
(`majority_verdict`), the speaking order is fixed (`speaking_order`), and a change that asks for a
term the profile does not state is marked "to acquire" (`needs_skill`, `committee_changes`).
The texts read by January are shortened (`Prose`) rather than refused; the number of changes
(exactly three) is checked and sent back to the model (`structured_call`)."""

from collections import Counter
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, BeforeValidator, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import CvContent, MasterProfileData, facts_of
from app.agents.tools.kit_schema import CompanyDossier, CompanySize
from app.agents.tools.posting_schema import Keyword, PostingAnalysis, contains_term, normalize_term
from app.agents.tools.text_claims import Claim, text_claims

__all__ = [
    "LABELS",
    "MAX_OBJECTIONS",
    "MAX_WORDS",
    "PERSONAS",
    "AtsTermsView",
    "Change",
    "ChangeDraft",
    "CommitteeContext",
    "Persona",
    "PersonaVote",
    "RankedObjection",
    "Synthesis",
    "SynthesisDraft",
    "Verdict",
    "Vote",
    "ats_terms_of",
    "committee_changes",
    "cv_plain_text",
    "majority_verdict",
    "speaking_order",
]

Persona = Literal["ats_reader", "recruiter", "manager", "colleague"]
PERSONAS: tuple[Persona, ...] = get_args(Persona)  # machine filter, HR, manager, future colleague
Verdict = Literal["yes", "no", "maybe"]
_LEGACY_VERDICTS = {"oui": "yes", "non": "no", "peut_etre": "maybe"}


def _verdict(value: object) -> object:
    return _LEGACY_VERDICTS.get(value, value) if isinstance(value, str) else value


_SavedVerdict = Annotated[Verdict, BeforeValidator(_verdict)]
LABELS: dict[str, str] = {
    "ats_reader": "ATS reader",
    "recruiter": "Recruiter",
    "manager": "Manager",
    "colleague": "Future colleague",
}
MAX_WORDS = 150  # one speaking turn (SPEC 9.3)
MAX_OBJECTIONS = 6
CHANGES = 3
MAX_TERMS = 30
Sentence = Annotated[str, Field(min_length=1, max_length=300), ShortenToMax()]
ACQUIRE = "Build evidence for {terms} before adding this to your CV."
CHECK = "To check · Verify {terms} before adding these details to your CV."
# The words of a CV section: an instruction about the CV ("the Skills section"), not a name.
# French and English headings both stay: CVs and profiles written before the switch are French.
_SECTION_NAMES = (
    "Compétences Expériences Expérience Formation Formations Projets Langues Résumé Profil "
    "Certifications Intérêts Loisirs Bénévolat Publications "
    "Skills Experience Education Projects Summary Languages Certifications Interests Hobbies "
    "Volunteering Volunteer Publications"
)
SECTION_WORDS = frozenset(normalize_term(word, plural=True) for word in _SECTION_NAMES.split())


class Vote(BaseModel):
    """A persona's vote: an interview, yes, no or maybe, and its main objection."""

    vote: _SavedVerdict
    objection: Sentence
    reason: Prose = Field(min_length=1, max_length=500)


class PersonaVote(Vote):
    persona: Persona


class RankedObjection(BaseModel):
    """An objection of the committee (heaviest first) and the personas that carry it."""

    text: Sentence
    personas: list[Persona] = Field(default_factory=list, max_length=len(PERSONAS))


class ChangeDraft(BaseModel):
    """A change proposed by the Moderator: the persona whose vote it would flip and the
    profile facts to bring forward."""

    text: Sentence
    persona: Persona
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class Change(ChangeDraft):
    """A stored change. `needs_skill`: it asks for a term the profile does not state (`terms`);
    it is then a skill "to acquire", never an "add X"."""

    needs_skill: bool = False
    terms: list[str] = Field(default_factory=list, max_length=MAX_TERMS)


class SynthesisDraft(BaseModel):
    """What the Moderator writes: the ranking of the objections and the three changes."""

    objections: list[RankedObjection] = Field(min_length=1, max_length=MAX_OBJECTIONS)
    changes: list[ChangeDraft] = Field(min_length=CHANGES, max_length=CHANGES)


class Synthesis(BaseModel):
    """The verdict (set by the code), the ranked objections and the three changes."""

    verdict: _SavedVerdict
    objections: list[RankedObjection] = Field(max_length=MAX_OBJECTIONS)
    changes: list[Change] = Field(min_length=CHANGES, max_length=CHANGES)


class AtsTermsView(BaseModel):
    """The posting terms (keywords and tools) that the CV writes (`found`) and those it does not
    write (`missing`): enough to say which recruiter searches would surface the CV."""

    found: list[str] = Field(default_factory=list, max_length=MAX_TERMS)
    missing: list[str] = Field(default_factory=list, max_length=MAX_TERMS)


class CommitteeContext(BaseModel):
    """What the graph reads (read-only): the version's CV (text, without name or
    contact details), the posting, its dossier under 30 days old and the company size, the
    posting terms seen in the CV, the validated profile (to re-read the changes), the company
    and the exact job title."""

    cv_text: str
    posting_text: str
    analysis: PostingAnalysis
    dossier: CompanyDossier | None = None
    size: CompanySize = "unknown"
    ats_terms: AtsTermsView = Field(default_factory=AtsTermsView)
    profile: MasterProfileData
    company: str | None = None
    title: str


def majority_verdict(votes: list[PersonaVote]) -> Verdict:
    """The majority of the votes: more than half on the same answer. A tie or no majority
    (2 against 2, 2-1-1): "maybe" (SPEC F19)."""
    counts = Counter(vote.vote for vote in votes)
    for answer in get_args(Verdict):
        if counts[answer] * 2 > len(votes):
            return answer  # type: ignore[no-any-return]
    return "maybe"


def speaking_order(round_number: int) -> list[Persona]:
    """The speaking order, fixed by the code: that of the personas in round 1, shifted by one rank
    at each following round (the last speaker of a round does not speak first in the next)."""
    shift = (round_number - 1) % len(PERSONAS)
    return [*PERSONAS[shift:], *PERSONAS[:shift]]


def cv_plain_text(cv: CvContent) -> str:
    """The CV as read by the committee: headline and sections, without name or contact details."""
    lines = [cv.headline] if cv.headline else []
    for section in cv.sections:
        lines.append(f"## {section.title}")
        for entry in section.entries:
            head = " — ".join(p for p in (entry.heading, entry.subheading, entry.dates) if p)
            lines += [head, *(f"- {line.text}" for line in entry.lines)]
        lines += [f"- {line.text}" for line in section.items]
    return "\n".join(line for line in lines if line)


def _forms(keyword: Keyword) -> list[str]:
    return [keyword.term, *keyword.variants]


def ats_terms_of(analysis: PostingAnalysis, cv_text: str) -> AtsTermsView:
    """The posting's keywords and tools, written in the CV (one of their forms appears there,
    case, accents and simple plural ignored) or not. Code: no term is invented."""
    wanted = [_forms(keyword) for keyword in analysis.keywords]
    wanted += [[tool] for tool in analysis.tools]
    found: list[str] = []
    missing: list[str] = []
    for forms in wanted:
        term = forms[0]
        if term in found or term in missing:
            continue
        seen = any(contains_term(cv_text, form, plural=True) for form in forms)
        (found if seen else missing).append(term)
    return AtsTermsView(found=found[:MAX_TERMS], missing=missing[:MAX_TERMS])


def _section(claim: Claim) -> bool:
    return normalize_term(claim.term, plural=True) in SECTION_WORDS


def committee_changes(
    drafts: list[ChangeDraft], profile: MasterProfileData, allowed: list[str]
) -> list[Change]:
    """The Moderator's changes re-read by the code: the fact identifiers unknown to the
    profile are removed; a text that asks for a term the profile does not state (`text_claims`,
    `allowed`: the company and the exact job title only) becomes "to acquire", with these terms
    (tools, figures, titles), never keeping the model's "add X". A proper noun absent
    from the profile (employer, school) gives "to check" (`CHECK`); the section words of a CV
    (`SECTION_WORDS`) are not names."""
    known = set(facts_of(profile))
    changes: list[Change] = []
    for draft in drafts:
        claims = text_claims(draft.text, profile, allowed=allowed)
        skills = list(dict.fromkeys(c.term for c in claims if c.kind != "name"))[:MAX_TERMS]
        names = list(dict.fromkeys(c.term for c in claims if c.kind == "name" and not _section(c)))
        terms = skills or names[:MAX_TERMS]
        template = ACQUIRE if skills else CHECK
        text = template.format(terms=", ".join(terms)) if terms else draft.text
        facts = list(dict.fromkeys(f for f in draft.fact_ids if f in known))
        changes.append(
            Change(
                text=text,
                persona=draft.persona,
                fact_ids=facts,
                needs_skill=bool(terms),
                terms=terms,
            )
        )
    return changes
