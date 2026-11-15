"""Schémas du kit de candidature (SPEC 6.4, F16, D142) : les sept pièces écrites au nom de January
et le dossier de l'entreprise. Les longueurs en mots sont comptées par le code (un modèle ne
compte pas) : une pièce hors bornes après le seul nouvel essai reste « à vérifier ».

Chaque brouillon de texte expose `parts()` (les textes comptés et contrôlés par `text_claims`),
`limits` (mots min et max de chaque partie qui en a) et `render()` (le contenu rangé). Conventions
du contenu rangé, lues par d'autres tâches : `followups` = courriel de 7 jours, une ligne `---`,
courriel de 14 jours (7.3) ; `linkedin` = invitation, une ligne `---`, message.

Un texte de dossier cite ses sources par `[n]` (rang de la page lue) : le code retire toute
citation sans source lue (`kit_dossier`)."""

import datetime as dt
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.salary import is_salary_question
from app.db.models.applications import KitKind, KitStatus

__all__ = [
    "KIT_KINDS",
    "CompanyDossier",
    "CvVersionRef",
    "Draft",
    "FormAnswer",
    "FormAnswers",
    "Followups",
    "KitContext",
    "KitKind",
    "KitStatus",
    "Letter",
    "LinkedInMessages",
    "NewsItem",
    "Pitch",
    "SourceRef",
    "join_parts",
]

KIT_KINDS: tuple[KitKind, ...] = (
    "cv",
    "letter",
    "linkedin",
    "followups",
    "form_answers",
    "company_brief",
    "pitch",
)
SEPARATOR = "---"
SALARY_BLANK = "À remplir par toi"
TO_COMPLETE = "À compléter"
NO_QUESTION = "Aucune question éliminatoire repérée dans l'offre."


def join_parts(first: str, second: str) -> str:
    """Deux textes séparés par une ligne `---` (une ligne `---` d'un texte est retirée)."""
    clean = [
        "\n".join(line for line in text.splitlines() if line.strip() != SEPARATOR).strip()
        for text in (first, second)
    ]
    return f"{clean[0]}\n\n{SEPARATOR}\n\n{clean[1]}"


class Draft(BaseModel):
    """Un brouillon de texte : ce que le code compte (`limits`) et contrôle (`parts`)."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {}

    def parts(self) -> dict[str, str]:
        raise NotImplementedError

    def render(self) -> str:
        raise NotImplementedError


class Letter(Draft):
    """Lettre de motivation : 250 à 350 mots, dans la langue de l'offre."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"text": (250, 350)}
    text: Prose = Field(min_length=1, max_length=4000)

    def parts(self) -> dict[str, str]:
        return {"text": self.text}

    def render(self) -> str:
        return self.text.strip()


class LinkedInMessages(Draft):
    """Invitation (300 caractères au plus, plafond de LinkedIn) et message (150 mots au plus)."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"message": (1, 150)}
    invitation: str = Field(min_length=1, max_length=300)
    message: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"invitation": self.invitation, "message": self.message}

    def render(self) -> str:
        return join_parts(self.invitation, self.message)


class Followups(Draft):
    """Courriels de relance à 7 et à 14 jours, 120 mots au plus chacun."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"day_7": (1, 120), "day_14": (1, 120)}
    day_7: Prose = Field(min_length=1, max_length=2000)
    day_14: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"day_7": self.day_7, "day_14": self.day_14}

    def render(self) -> str:
        return join_parts(self.day_7, self.day_14)


class Pitch(Draft):
    """« Parle-moi de toi » : 130 à 170 mots, soit 60 secondes à voix haute."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"text": (130, 170)}
    text: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"text": self.text}

    def render(self) -> str:
        return self.text.strip()


class FormAnswer(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(max_length=800)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)  # faits qui l'appuient

    @property
    def state(self) -> Literal["ok", "salary", "to_complete"]:
        """« À remplir par toi » : question salariale (réponse vidée par le code) ; « À
        compléter » : aucun fait du profil n'appuie la réponse."""
        if self.answer.strip():
            return "ok"
        return "salary" if is_salary_question(self.question) else "to_complete"


class FormAnswers(Draft):
    """Réponses aux questions éliminatoires de l'offre, tirées du profil seulement."""

    items: list[FormAnswer] = Field(default_factory=list, max_length=10)

    def parts(self) -> dict[str, str]:
        return {f"answer_{rank}": item.answer for rank, item in enumerate(self.items, 1)}

    def render(self) -> str:
        if not self.items:
            return NO_QUESTION
        blanks = {"salary": SALARY_BLANK, "to_complete": TO_COMPLETE}
        lines = []
        for item in self.items:
            body = item.answer if item.state == "ok" else blanks[item.state]
            lines.append(f"### {item.question}\n{body}")
        return "\n\n".join(lines)


Cited = Annotated[str, Field(min_length=1, max_length=300)]


class NewsItem(BaseModel):
    """Une actualité : datée (moins de 6 mois) et citée `[n]` dans son texte."""

    text: Prose = Field(min_length=1, max_length=300)
    date: dt.date | None = None


class CompanyDossier(BaseModel):
    """Le dossier d'une page sur l'entreprise (F16) : chaque texte cite ses sources par `[n]`."""

    activity: Prose = Field(max_length=700)
    product: Prose = Field(max_length=700)
    stack: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=15
    )
    news: list[NewsItem] = Field(default_factory=list, max_length=8)
    culture: Prose = Field(max_length=700)
    interview_process: Prose = Field(max_length=700)
    questions: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=5, max_length=5
    )
    watch_points: list[Cited] = Field(default_factory=list, max_length=6)
    size: Literal["startup", "pme", "grand_groupe", "inconnu"] = "inconnu"


class SourceRef(BaseModel):
    """Une page lue, citée par son rang (`[n]` = rang + 1) dans le dossier."""

    url: str = Field(max_length=2048)
    title: str = Field(default="", max_length=300)
    source_id: str | None = None


class CvVersionRef(BaseModel):
    """La version de CV prête la plus récente de l'offre."""

    version_id: str
    number: int = Field(ge=1)


class KitContext(BaseModel):
    """Ce que le kit lit (lecture seule) : la fiche, son offre analysée, le profil validé, le
    dossier de moins de 30 jours (`company_dossier`, ses pages dans `company_dossier_sources`), la
    version de CV prête, les pièces que January a modifiées (`keep` : jamais refaites), son jour
    (`today`, fuseau de ses réglages) et le nom du contact s'il y en a un."""

    application_id: str
    language: Literal["fr", "en"]
    today: dt.date
    posting_text: str
    analysis: PostingAnalysis
    company: str
    title: str
    contact: str | None = None
    profile: MasterProfileData
    company_dossier: CompanyDossier | None = None
    company_dossier_sources: list[SourceRef] = Field(default_factory=list)
    cv_version: CvVersionRef | None = None
    keep: list[KitKind] = Field(default_factory=list)
