"""Ce que proposent le Lecteur ATS et le Recruteur pour un CV ciblé (SPEC 5.3, F9) : modifications
rangées par référence, positions du Recruteur face aux propositions du Lecteur, fiche entreprise.
Le moteur n'importe aucune feature (contrat 6) : ces types vivent donc ici.

Un modèle ne cite que des identifiants de faits (`x1a2`) ; ce que dit le texte `after` est contrôlé
par le validateur (`cv_validator`), pas ici.
"""

from collections.abc import Sequence
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import (
    MasterProfileData,
    ModificationAction,
    ModificationType,
    SectionKey,
    facts_of,
    in_cv,
)

# Un identifiant de fait du profil (voir l'en-tête de `cv_schema`) : préfixe par genre, puis un
# numéro **sans borne** (« c100 » est permis), puis éventuellement `a`/`d` et le numéro de l'enfant.
FACT_ID = r"^[xfcplkts]\d+([ad]\d+)?$"
FactId = Annotated[str, Field(pattern=FACT_ID)]
_SECTION_OF_PREFIX: dict[str, SectionKey] = {
    "t": "summary",
    "s": "summary",
    "x": "experience",
    "f": "education",
    "c": "skills",
    "p": "projects",
    "l": "languages",
    "k": "links",
}
_SECTIONS: tuple[str, ...] = get_args(SectionKey)


def section_of(fact_id: str) -> SectionKey | None:
    """La section du CV qui porte le fait (le titre et le résumé : « summary »)."""
    return _SECTION_OF_PREFIX.get(fact_id[:1])


class Proposal(BaseModel):
    """Une modification proposée. `ref` : `a` Lecteur ATS, `r` Recruteur. `after` : le nouveau
    texte (vide pour `remove` ; pour `move`, la clé de la section avant laquelle `section` passe).
    """

    ref: str = Field(pattern=r"^[ar]\d{1,2}$")
    section: SectionKey
    action: ModificationAction
    target: str | None = Field(default=None, pattern=FACT_ID)
    after: str = Field(default="", max_length=600)
    reason: Prose = Field(min_length=1, max_length=300)
    type: ModificationType
    fact_ids: list[FactId] = Field(default_factory=list, max_length=6)


class ProposalList(BaseModel):
    items: list[Proposal] = Field(max_length=25)


_Note = Annotated[str, Field(max_length=300), ShortenToMax()]


class AtsReading(ProposalList):
    """Sortie du Lecteur ATS (D129) : ses propositions et ses notes sur la lecture du CV par
    l'ATS de l'offre (rapport, `ats_notes`)."""

    notes: list[_Note] = Field(default_factory=list, max_length=6)


class RecruiterReading(ProposalList):
    """Sortie du Recruteur (D129) : ses propositions, les forces et les risques du CV face à
    l'offre (rapport)."""

    strengths: list[_Note] = Field(default_factory=list, max_length=5)
    risks: list[_Note] = Field(default_factory=list, max_length=5)


class Stance(BaseModel):
    """La position du Recruteur sur une proposition du Lecteur ATS (`ref` : la sienne)."""

    ref: str
    stance: Literal["keep", "drop", "amend"]
    after: str | None = Field(default=None, max_length=600)
    reason: Prose = Field(min_length=1, max_length=300)


class Confrontation(BaseModel):
    stances: list[Stance] = Field(max_length=50)


class CompanyBrief(BaseModel):
    """Fiche entreprise : ce que dit l'offre, rien d'autre."""

    summary: Prose = Field(min_length=1, max_length=800)
    values: list[Annotated[str, Field(max_length=120)]] = Field(max_length=6)
    stack: list[Annotated[str, Field(max_length=80)]] = Field(max_length=15)
    tone: str | None = Field(default=None, max_length=80)


def _target_problems(p: Proposal, facts: dict[str, str], cv_ids: set[str]) -> list[str]:
    ref = p.ref
    if p.action == "move":
        if p.after not in _SECTIONS or p.after == p.section:
            return [
                f"La proposition {ref} déplace une section : `after` doit être la clé d'une autre "
                "section."
            ]
        return []
    if p.target is None:
        return [
            f"La proposition {ref} ({p.action}) doit viser un fait du profil : renseigne `target`."
        ]
    if p.target not in facts:
        return [
            f"La proposition {ref} vise un fait qui n'est pas dans le profil : corrige `target`."
        ]
    out: list[str] = []
    if section_of(p.target) != p.section:
        out.append(f"La proposition {ref} vise un fait d'une autre section que `section`.")
    if p.action == "add" and p.target in cv_ids:
        out.append(
            f"La proposition {ref} ajoute un fait déjà dans le CV : "
            "propose plutôt une reformulation."
        )
    if p.action in ("remove", "rewrite") and p.target not in cv_ids:
        out.append(
            f"La proposition {ref} ({p.action}) vise un fait absent du CV : "
            "propose plutôt un ajout."
        )
    if p.action in ("add", "rewrite") and not p.after.strip():
        out.append(f"La proposition {ref} ({p.action}) n'a pas de texte : renseigne `after`.")
    return out


def proposal_problems(items: Sequence[Proposal], profile: MasterProfileData) -> list[str]:
    """Une phrase française, rendue au modèle, par défaut : référence en double, fait inconnu
    (`target` ou `fact_ids`), `add` d'un fait déjà dans le CV, `remove` ou `rewrite` d'un fait
    absent du CV, section qui n'est pas celle du fait, texte manquant, `move` sans section cible.
    Aucune phrase ne recopie le texte d'une proposition."""
    facts = facts_of(profile)
    cv_ids = in_cv(profile)
    problems: list[str] = []
    seen: set[str] = set()
    for p in items:
        if p.ref in seen:
            problems.append(
                f"La référence {p.ref} est utilisée deux fois : une référence par proposition."
            )
        seen.add(p.ref)
        problems += _target_problems(p, facts, cv_ids)
        unknown = [fact for fact in p.fact_ids if fact not in facts]
        if unknown:
            problems.append(
                f"La proposition {p.ref} cite des faits absents du profil ({', '.join(unknown)}) : "
                "retire-les ou corrige leurs identifiants."
            )
    return problems
