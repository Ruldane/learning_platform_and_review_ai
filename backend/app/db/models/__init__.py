# Importer ici chaque module de modèles : Alembic et les tests lisent `Base.metadata`.
from app.db.models import accounts, agents, learning, lessons, memory, program, research, skills

__all__ = ["accounts", "agents", "learning", "lessons", "memory", "program", "research", "skills"]
