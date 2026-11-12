"""Schémas et constantes de l'Éclaireur (SPEC 9.1, 10.3). Les bornes de la note sont celles du
barème : le schéma les fait respecter, une note hors barème fait rejouer le modèle puis échouer
lisiblement (`structured_output_invalid`), jamais passer."""

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.agents.state.web_research import WebResearchState

AGENT = "scout"
MAX_PAGES_PER_RUN = 10  # borné aussi par le plafond de pages de la session
MAX_EXTRA_URLS = 5  # adresses données en entrée, lues en plus des résultats
# Pages notées au plus par un nœud `judge` : résultats lus plus adresses de l'entrée.
MAX_PAGES_JUDGED = MAX_PAGES_PER_RUN + MAX_EXTRA_URLS
PAGE_CHARS_FOR_SCORING = 6000
MAX_QUERIES_TOTAL = 6
QUERIES_PER_LANGUAGE = 3


class Node(Protocol):
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: WebResearchState) -> WebResearchState: ...


class PlannedQuery(BaseModel):
    text: str = Field(min_length=2, max_length=200)
    lang: str = Field(pattern=r"^[a-z]{2}$")


class SearchPlan(BaseModel):
    queries: list[PlannedQuery] = Field(min_length=1, max_length=MAX_QUERIES_TOTAL)


class SourceScore(BaseModel):
    """Barème de 10.3 : autorité 30 + fraîcheur 20 + profondeur 20 + auteur réel 15 + qualité
    pédagogique 15. Le modèle ne donne pas le total : le code l'additionne."""

    authority: int = Field(ge=0, le=30)
    freshness: int = Field(ge=0, le=20)
    depth: int = Field(ge=0, le=20)
    author: int = Field(ge=0, le=15)
    pedagogy: int = Field(ge=0, le=15)
    reason: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=600)

    @property
    def total(self) -> int:
        return self.authority + self.freshness + self.depth + self.author + self.pedagogy

    @property
    def criteria(self) -> dict[str, int]:
        return {
            "authority": self.authority,
            "freshness": self.freshness,
            "depth": self.depth,
            "author": self.author,
            "pedagogy": self.pedagogy,
        }


def one_line(text: str) -> str:
    return " ".join(text.split())


def page_title(page: dict[str, Any]) -> str:
    """Titre de la page sur une ligne, sinon son adresse."""
    return one_line(page.get("title") or "") or str(page["url"])
