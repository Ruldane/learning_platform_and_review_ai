"""L'empreinte d'un fichier de l'IDE (P9), sans dépendance : les schémas et les services la
partagent."""

import hashlib
import re

_HASH = re.compile(r"[0-9a-f]{64}")


def file_hash(content: str) -> str:
    """L'empreinte d'un fichier : sha256 hexadécimal, en minuscules, du contenu en UTF-8."""
    return hashlib.sha256(content.encode()).hexdigest()


def is_file_hash(value: str | None) -> bool:
    """Vrai pour 64 chiffres hexadécimaux en minuscules."""
    return value is not None and _HASH.fullmatch(value) is not None
