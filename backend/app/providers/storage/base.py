"""Port du stockage de fichiers. Le nom de fichier reçu n'entre jamais dans un chemin : la clé
est générée (`<user_id>/<catégorie>/<uuid4><suffixe canonique>`) et seule elle est conservée."""

from typing import Protocol

from app.core.errors import AppError

ALLOWED_SUFFIXES = (".pdf", ".docx", ".md", ".txt")


class StorageKeyInvalid(AppError):
    """Clé, utilisateur, catégorie ou suffixe hors du format attendu (ou hors du dossier racine).
    Le message ne cite jamais la valeur refusée."""

    def __init__(self) -> None:
        super().__init__("storage_key_invalid", "Chemin de fichier refusé.", status_code=400)


class FileStorage(Protocol):
    async def save(self, user_id: str, category: str, data: bytes, suffix: str) -> str:
        """Écrit `data` et rend la clé relative générée."""
        ...

    async def read(self, user_id: str, key: str) -> bytes:
        """La clé doit appartenir à `user_id` (préfixe `<user_id>/`), sinon `StorageKeyInvalid`."""
        ...

    async def delete(self, user_id: str, key: str) -> None:
        """Idempotent : une clé déjà supprimée ne lève rien. Même contrôle d'appartenance."""
        ...
