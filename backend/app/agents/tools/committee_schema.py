"""Schémas du comité de recrutement simulé (SPEC F19, D147) : les quatre personas, leur vote, la
synthèse du Modérateur et le contexte que le parcours `hiring_committee` lit.

Ce que le code décide, le modèle ne le choisit pas : le verdict est la majorité des quatre votes
(`majority_verdict`), l'ordre de parole est fixe (`speaking_order`), et un changement qui demande un
terme que le profil ne dit pas est marqué « à acquérir » (`needs_skill`, `committee_changes`).
Les textes lus par January sont raccourcis (`Prose`) plutôt que refusés ; le nombre de changements
(trois exactement) est vérifié et renvoyé au modèle (`structured_call`)."""

from collections import Counter
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import CvContent, MasterProfileData, facts_of
from app.agents.tools.kit_schema import CompanyDossier
from app.agents.tools.posting_schema import Keyword, PostingAnalysis, contains_term
from app.agents.tools.text_claims import text_claims

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
    "Size",
    "VERDICT_WORDS",
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
PERSONAS: tuple[Persona, ...] = get_args(Persona)  # filtre machine, RH, manager, futur collègue
Verdict = Literal["oui", "non", "peut_etre"]
Size = Literal["startup", "pme", "grand_groupe", "inconnu"]
LABELS: dict[str, str] = {
    "ats_reader": "Lecteur ATS",
    "recruiter": "Recruteur",
    "manager": "Manager",
    "colleague": "Futur collègue",
}
MAX_WORDS = 150  # une prise de parole (SPEC 9.3)
VERDICT_WORDS: dict[str, str] = {"oui": "oui", "non": "non", "peut_etre": "peut-être"}
MAX_OBJECTIONS = 6
CHANGES = 3
MAX_TERMS = 30
Sentence = Annotated[str, Field(min_length=1, max_length=300), ShortenToMax()]
ACQUIRE = "À acquérir : {terms}. Ton profil ne le dit pas : ne l'écris pas dans ton CV."


class Vote(BaseModel):
    """Le vote d'une persona : un entretien, oui, non ou peut-être, et son objection principale."""

    vote: Verdict
    objection: Sentence
    reason: Prose = Field(min_length=1, max_length=500)


class PersonaVote(Vote):
    persona: Persona


class RankedObjection(BaseModel):
    """Une objection du comité (les plus lourdes d'abord) et les personas qui la portent."""

    text: Sentence
    personas: list[Persona] = Field(default_factory=list, max_length=len(PERSONAS))


class ChangeDraft(BaseModel):
    """Un changement proposé par le Modérateur : la persona dont il ferait basculer le vote et les
    faits du profil à mettre en avant."""

    text: Sentence
    persona: Persona
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class Change(ChangeDraft):
    """Un changement rangé. `needs_skill` : il demande un terme que le profil ne dit pas (`terms`) ;
    c'est alors une compétence « à acquérir », jamais un « ajoute X »."""

    needs_skill: bool = False
    terms: list[str] = Field(default_factory=list, max_length=MAX_TERMS)


class SynthesisDraft(BaseModel):
    """Ce que le Modérateur écrit : le classement des objections et les trois changements."""

    objections: list[RankedObjection] = Field(min_length=1, max_length=MAX_OBJECTIONS)
    changes: list[ChangeDraft] = Field(min_length=CHANGES, max_length=CHANGES)


class Synthesis(BaseModel):
    """Le verdict (fixé par le code), les objections classées et les trois changements."""

    verdict: Verdict
    objections: list[RankedObjection] = Field(max_length=MAX_OBJECTIONS)
    changes: list[Change] = Field(min_length=CHANGES, max_length=CHANGES)


class AtsTermsView(BaseModel):
    """Les termes de l'offre (mots clés et outils) que le CV écrit (`found`) et ceux qu'il n'écrit
    pas (`missing`) : de quoi dire quelles recherches de recruteur feraient remonter le CV."""

    found: list[str] = Field(default_factory=list, max_length=MAX_TERMS)
    missing: list[str] = Field(default_factory=list, max_length=MAX_TERMS)


class CommitteeContext(BaseModel):
    """Ce que le parcours lit (lecture seule) : le CV de la version (texte, sans nom ni
    coordonnées), l'offre, son dossier de moins de 30 jours et la taille de l'entreprise, les
    termes de l'offre vus dans le CV, le profil validé (pour relire les changements), l'entreprise
    et l'intitulé exact du poste."""

    cv_text: str
    posting_text: str
    analysis: PostingAnalysis
    dossier: CompanyDossier | None = None
    size: Size = "inconnu"
    ats_terms: AtsTermsView = Field(default_factory=AtsTermsView)
    profile: MasterProfileData
    company: str | None = None
    title: str


def majority_verdict(votes: list[PersonaVote]) -> Verdict:
    """La majorité des votes : plus de la moitié sur la même réponse. Égalité ou aucune majorité
    (2 contre 2, 2-1-1) : « peut-être » (SPEC F19)."""
    counts = Counter(vote.vote for vote in votes)
    for answer in get_args(Verdict):
        if counts[answer] * 2 > len(votes):
            return answer  # type: ignore[no-any-return]
    return "peut_etre"


def speaking_order(round_number: int) -> list[Persona]:
    """L'ordre de parole, fixé par le code : celui des personas au tour 1, décalé d'un rang à
    chaque tour suivant (le dernier orateur d'un tour ne parle pas le premier du suivant)."""
    shift = (round_number - 1) % len(PERSONAS)
    return [*PERSONAS[shift:], *PERSONAS[:shift]]


def cv_plain_text(cv: CvContent) -> str:
    """Le CV lu par le comité : accroche et sections, sans nom ni coordonnées."""
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
    """Les mots clés et outils de l'offre, écrits dans le CV (une de leurs formes y figure, casse,
    accents et pluriel simple ignorés) ou non. Du code : aucun terme n'est inventé."""
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


def committee_changes(
    drafts: list[ChangeDraft], profile: MasterProfileData, allowed: list[str]
) -> list[Change]:
    """Les changements du Modérateur relus par le code : les identifiants de faits inconnus du
    profil sont retirés ; un texte qui demande un terme que le profil ne dit pas (`text_claims`,
    `allowed` : l'entreprise et l'intitulé exact seulement) devient « à acquérir », avec ces termes
    (outils, chiffres, titres), sans jamais garder le « ajoute X » du modèle."""
    known = set(facts_of(profile))
    changes: list[Change] = []
    for draft in drafts:
        claims = text_claims(draft.text, profile, allowed=allowed)
        # Les noms propres ne comptent pas : un changement est une consigne sur le CV (« la
        # section Compétences »), pas une phrase de January ; outils, chiffres et titres, si.
        named = [claim.term for claim in claims if claim.kind != "name"]
        terms = list(dict.fromkeys(named))[:MAX_TERMS]
        text = ACQUIRE.format(terms=", ".join(terms)) if terms else draft.text
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
