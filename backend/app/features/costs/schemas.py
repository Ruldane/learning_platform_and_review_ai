from datetime import date, datetime

from pydantic import BaseModel


class CostTotals(BaseModel):
    """Appels, jetons et coût d'un groupe d'appels ; `estimated_calls` : combien de ces appels
    ont un coût estimé (le fournisseur n'a pas rendu ses jetons)."""

    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    estimated_calls: int


class CostRow(CostTotals):
    """Une ligne du rapport. `key` : le jour (`2026-11-16`), le graphe (`""` hors session),
    l'agent (`""` aucun) ou `fournisseur:modèle` (`glm:glm-5.3-flash`)."""

    key: str


class CostsReport(BaseModel):
    """Les coûts des `days` derniers jours locaux, de `since` à `until` inclus ; les jours sans
    appel sont présents, à zéro."""

    days: int
    since: date
    until: date
    total: CostTotals
    by_day: list[CostRow]
    by_feature: list[CostRow]
    by_agent: list[CostRow]
    by_model: list[CostRow]


class AgentCallOut(BaseModel):
    """Un appel à un modèle, tel que journalisé : jamais le contenu du prompt."""

    id: str
    at: datetime
    session_id: str | None
    graph: str | None
    agent: str | None
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float
    estimated: bool


class AgentCallPage(BaseModel):
    """Une page du journal ; `next_before` (curseur opaque) donne la page suivante, `None` à la
    fin."""

    items: list[AgentCallOut]
    next_before: str | None
