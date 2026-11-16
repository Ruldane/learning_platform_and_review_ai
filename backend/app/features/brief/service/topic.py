"""Le sujet de la ressource du brief (F17, D161) : « {domaine visé} actualités », construit par le
code, jamais par un modèle. Le domaine vient, dans l'ordre : du poste des réglages du radar, du
poste du dernier objectif, d'un court sujet tiré du texte de ce dernier objectif (le verbe
« Devenir » ou « Become » en tête retiré, une seule ligne, `MAX_TOPIC` caractères au plus), puis du
titre du programme validé. Rien de tout cela : `None`, aucune recherche. Le sujet est une donnée
de la requête et du prompt (cadré `untrusted`) ; il n'est jamais journalisé."""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.service.goals import list_goals
from app.features.program.service.programs import list_programs
from app.features.radar.service.runs import defaults

TOPIC_SUFFIX = "actualités"
MAX_TOPIC = 80  # caractères du domaine tiré d'un texte libre

_VERB = re.compile(
    r"^(?:devenir|become)\b\s*(?:(?:une?|le|la|les|an?|the)\b\s*|l['’]\s*)?", re.IGNORECASE
)
_SENTENCE_END = re.compile(r"[.!?;:]")


def _cap(text: str) -> str:
    """`text` coupé à `MAX_TOPIC` caractères, sur un mot si possible."""
    if len(text) <= MAX_TOPIC:
        return text
    head = text[:MAX_TOPIC]
    return head.rsplit(" ", 1)[0] if " " in head else head


def goal_topic(text: str) -> str | None:
    """Un court sujet tiré du texte libre d'un objectif : une seule ligne, sans le verbe « Devenir »
    ou « Become » ni l'article qui le suit, coupée à la première phrase puis à `MAX_TOPIC`
    caractères (sur un mot). `None` si rien n'en reste."""
    line = _VERB.sub("", " ".join(text.split()), count=1)
    return _cap(_SENTENCE_END.split(line, maxsplit=1)[0].strip()).strip() or None


async def resource_topic(db: AsyncSession, user_id: str) -> str | None:
    """Le sujet de recherche de la ressource du jour, `None` s'il n'y a aucun domaine connu."""
    role, _zone = await defaults(db, user_id)
    if role:
        return f"{role} {TOPIC_SUFFIX}"
    goals = await list_goals(db, user_id)
    if goals and (topic := goal_topic(goals[0].text)) is not None:
        return f"{topic} {TOPIC_SUFFIX}"
    programs = await list_programs(db, user_id)
    current = next((p for p in programs if p.status == "validated"), None)
    title = " ".join(current.title.split()) if current is not None else ""
    return f"{title} {TOPIC_SUFFIX}" if title else None
