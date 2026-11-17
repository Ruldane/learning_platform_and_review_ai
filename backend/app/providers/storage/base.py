"""Port du stockage de fichiers. Le nom de fichier reçu n'entre jamais dans un chemin : la clé
est générée (`<user_id>/<catégorie>/<uuid4><suffixe canonique>`) et seule elle est conservée."""

from typing import Protocol

from app.core.errors import AppError

# Documents importés ; images des pages et polices d'un gabarit de CV (D119) ; captures d'un projet
# (PNG, JPEG, WebP : D166).
ALLOWED_SUFFIXES = (".pdf", ".docx", ".md", ".txt", ".png", ".jpg", ".webp", ".woff2", ".ttf")


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

    async def list_user(self, user_id: str) -> list[str]:
        """Les clés de tous les fichiers de `user_id` (la forme que `save` rend, préfixe
        `<user_id>/` compris), triées. Jamais un fichier d'un autre utilisateur ni un résidu
        d'écriture ; `StorageKeyInvalid` si `user_id` n'a pas la forme attendue."""
        ...

    async def delete_user(self, user_id: str) -> int:
        """Efface tout le dossier de `user_id` (résidus d'écriture compris) et rend le nombre de
        fichiers rangés qu'il contenait. Idempotent : sans dossier, rend 0. Jamais un fichier d'un
        autre utilisateur ; `StorageKeyInvalid` si `user_id` n'a pas la forme attendue ou si son
        dossier est un lien qui sort de la racine."""
        ...
