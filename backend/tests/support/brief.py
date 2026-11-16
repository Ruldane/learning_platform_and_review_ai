"""Faux port du brief du jour (`FakeBriefStore`) en mémoire, idempotent comme le contrat (D161) :
la première écriture de chaque rubrique gagne, `context` rend ce qui est déjà rangé. Aucun réseau
ni LLM."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.agents.tools.brief_port import AdviceFacts, BriefContext
from app.agents.tools.brief_schema import ResourceView
from app.features.brief.service.rules import advice_numbers

BRIEF_ID = "00000000-0000-4000-8000-0000000000b1"
TOPIC = "Les agents avec LangGraph"
BLOCK = "Construire un graphe d'agents"

FACTS = AdviceFacts(
    block_title=BLOCK,
    block_minutes=45,
    cards_due=12,
    reminders_due=2,
    offers=6,
    best_score=85,
    week_planned=5,
    week_done=4,
    streak_days=7,
)


def allowed_of(facts: AdviceFacts) -> frozenset[str]:
    """Les nombres permis : ceux des faits (la règle de la feature `brief`)."""
    return frozenset(
        advice_numbers(
            {
                "minutes": facts.block_minutes,
                "cards": facts.cards_due,
                "reminders": facts.reminders_due,
                "offers": facts.offers,
                "score": facts.best_score,
                "planned": facts.week_planned,
                "done": facts.week_done,
                "streak": facts.streak_days,
            }
        )
    )


@dataclass
class FakeBriefStore:
    topic: str | None = TOPIC
    facts: AdviceFacts = FACTS
    language: Literal["fr", "en"] = "fr"
    resource: ResourceView | None = None
    advice: list[str] | None = None
    resource_saved: bool = False  # `resource_done` : la rubrique est rangée (même vide)
    advice_saved: bool = False
    resource_saves: int = 0  # appels à `save_resource` (la première écriture gagne)
    advice_saves: int = 0
    advice_unavailable: bool = False  # le port a su que le modèle manquait (aucune clé)
    extra_allowed: frozenset[str] = field(default_factory=frozenset)

    async def context(self, user_id: str, brief_id: str) -> BriefContext:
        return BriefContext(
            brief_id,
            date(2026, 11, 16),
            self.language,
            self.topic,
            self.facts,
            self.resource_saved,
            self.advice_saved,
            allowed_of(self.facts) | self.extra_allowed,
        )

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None:
        self.resource_saves += 1
        if not self.resource_saved:
            self.resource, self.resource_saved = resource, True

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None:
        self.advice_saves += 1
        if not self.advice_saved:
            self.advice, self.advice_saved = sentences, True
            self.advice_unavailable = unavailable
