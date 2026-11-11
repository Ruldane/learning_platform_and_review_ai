"""État du parcours `learned_document` : un document marqué « déjà appris » devient des acquis."""

from typing import Any, TypedDict


class LearnedDocumentState(TypedDict, total=False):
    document_id: str
    title: str  # titre du document, repris dans la raison de chaque écriture
    text: str  # premiers fragments du document, joints
    known: str  # acquis déjà en mémoire (`SkillsSummary.as_text`)
    concepts: list[dict[str, Any]]  # `Concept.model_dump()`, dans l'ordre du modèle
    created: int  # acquis écrits
    already_known: int  # acquis déjà en mémoire (rien d'écrit)
    summary: str
