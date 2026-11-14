"""Le CV dans la vie de l'application (D124, D126) : ce que les routes du profil maître et des
gabarits partagent avec les ports de l'Archiviste (`AgentProfileStore`) et du Maquettiste
(`AgentCvTemplateStore`) : base, mémoire (documents rangés, fichiers relus, stockage des images et
des polices), lanceur de sessions (lié au moteur ensuite), mise en page des PDF, rendu de nos
gabarits HTML, polices libres et verrous. Créé par le lifespan avant le moteur d'agents
(`app.state.career.cv`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.providers.fonts.base import FontSource
from app.providers.pdf.base import HtmlPdfRenderer, PdfLayoutExtractor
from app.providers.storage.base import FileStorage

CAPTURE_GRAPH = "cv_capture"
PROFILE_SUBJECT = "master_profile"
TEMPLATE_SUBJECT = "cv_template"
REVIEW_GRAPH = "cv_review"
REVIEW_SUBJECT = "cv_review"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Resumer(Protocol):
    """Reprise d'une question en attente (`SessionLauncher.resume`, D130) : « Générer le PDF »
    répond à la question de sortie de la revue."""

    async def resume(
        self, user_id: str, session_id: str, interrupt_id: str, value: Any
    ) -> None: ...


class _NoResumer:
    """Valeur par défaut (tests du port, démarrages sans moteur) : moteur indisponible."""

    async def resume(self, user_id: str, session_id: str, interrupt_id: str, value: Any) -> None:
        raise AppError("engine_unavailable", "Le moteur d'agents n'est pas prêt.", 503)


@dataclass
class CvRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    memory: MemoryRuntime
    launcher: Launcher
    layout: PdfLayoutExtractor
    html_pdf: HtmlPdfRenderer
    fonts: FontSource
    now: Callable[[], datetime] = utc_now
    resumer: Resumer = field(default_factory=_NoResumer)
    _versions: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _imports: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _templates: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _reviews: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)

    @property
    def storage(self) -> FileStorage:
        """Le stockage de la mémoire : images des pages et polices des gabarits (D119)."""
        return self.memory.providers.storage

    def version_lock(self, user_id: str) -> asyncio.Lock:
        """Une nouvelle version du profil à la fois par utilisateur (brouillon de l'Archiviste,
        version de January) : numéros sans course. Propre à ce processus (un seul worker) ; l'index
        unique `(user_id, version)` reste le dernier rempart."""
        return self._versions.setdefault(user_id, asyncio.Lock())

    def import_lock(self, user_id: str) -> asyncio.Lock:
        """« Capture ouverte ? sinon lancer » : un double envoi ne lance qu'une capture."""
        return self._imports.setdefault(user_id, asyncio.Lock())

    def template_lock(self, user_id: str) -> asyncio.Lock:
        """Gabarits de l'utilisateur : création et lancement de la capture, statut rapproché de
        la session, gabarit actif (un seul, index unique partiel) ; jamais pendant un rendu."""
        return self._templates.setdefault(user_id, asyncio.Lock())

    def review_lock(self, user_id: str) -> asyncio.Lock:
        """Revues de l'utilisateur (D130) : lancement, statut rapproché de la session, décisions,
        clic sur « Générer » (décisions figées, une version en rendu à la fois) ; jamais pendant
        le rendu lui-même, que le parcours fait hors de ce verrou."""
        return self._reviews.setdefault(user_id, asyncio.Lock())
