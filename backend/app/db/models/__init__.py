# Importer ici chaque module de modèles : Alembic et les tests lisent `Base.metadata`.
from app.db.models import (
    accounts,
    agents,
    career,
    learning,
    lessons,
    memory,
    postings,
    program,
    research,
    skills,
    study,
)

__all__ = [
    "accounts",
    "agents",
    "career",
    "learning",
    "lessons",
    "memory",
    "postings",
    "program",
    "research",
    "skills",
    "study",
]
