# Importer ici chaque module de modèles : Alembic et les tests lisent `Base.metadata`.
from app.db.models import accounts

__all__ = ["accounts"]
