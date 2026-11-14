"""Port du profil maître (SPEC 5.1, D124). `app.agents` n'importe aucune feature (contrat 6) : il
décrit ici ce dont l'Archiviste a besoin en mode `profile` (le texte des documents de January,
la dernière version validée, l'écriture du brouillon) ; la feature `cv` l'implémente
(`AgentProfileStore`, 6.8).

Le texte d'un CV, d'un profil LinkedIn et la note de January sont des données personnelles et un
contenu non fiable (17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation.

`save_draft` est idempotent par session : un nœud rejoué après un arrêt (SPEC 9.4) rend le numéro
du brouillon déjà écrit, sans en écrire un second."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.cv_schema import MasterProfileData
from app.core.errors import AppError

SourceKind = Literal["cv", "linkedin", "note"]
MAX_SOURCE_CHARS = 40_000  # texte d'une source montré à l'Archiviste (coupé au-delà)
MAX_NOTE_CHARS = 4_000
MAX_HIDDEN_LINES = 20  # lignes de texte invisible gardées pour les montrer à January


@dataclass(frozen=True)
class ProfileSource:
    """Une source du profil : le texte visible d'un PDF (dans l'ordre du flux) ou la note."""

    kind: SourceKind
    text: str  # `MAX_SOURCE_CHARS` au plus


@dataclass(frozen=True)
class ProfileSources:
    """Les sources dans l'ordre CV, LinkedIn, note ; `previous` : dernière version validée.
    `hidden` : texte des lignes invisibles des PDF (texte blanc, minuscule, hors page), jamais
    montré à l'Archiviste et signalé à January dans `dropped` (preflight G6)."""

    sources: list[ProfileSource]
    previous: MasterProfileData | None
    hidden: list[str] = field(default_factory=list)


class ProfileStore(Protocol):
    async def sources(
        self, user_id: str, document_ids: Sequence[str], note: str | None
    ) -> ProfileSources:
        """Les PDF rangés dans la mémoire, relus par leur fichier et la mise en page (blocs
        visibles seulement), coupés à `MAX_SOURCE_CHARS` ; la note en dernier. Document absent
        ou d'une autre : 404 `document_not_found` ; PDF illisible : `PdfUnreadable`."""
        ...

    async def save_draft(
        self, user_id: str, session_id: str, draft: MasterProfileData, dropped: Sequence[str]
    ) -> int:
        """Idempotent par session (brouillon déjà écrit → son numéro). Fusion avec la dernière
        version validée (un fait au même texte normalisé garde son id), ids neufs jamais repris
        d'une version passée (`assign_fact_ids` en dernier) ; rend le numéro de version."""
        ...


def profile_unavailable() -> AppError:
    return AppError("profile_unavailable", "Le profil maître n'est pas branché sur ce moteur.", 503)


class _NoProfile:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def sources(
        self, user_id: str, document_ids: Sequence[str], note: str | None
    ) -> ProfileSources:
        raise profile_unavailable()

    async def save_draft(
        self, user_id: str, session_id: str, draft: MasterProfileData, dropped: Sequence[str]
    ) -> int:
        raise profile_unavailable()


NO_PROFILE: ProfileStore = _NoProfile()
