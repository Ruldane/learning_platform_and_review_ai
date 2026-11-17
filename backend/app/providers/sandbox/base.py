"""Le port `CodeSandbox` (phase 10, P5 à P7) : exécuter du code que January ou Claude a écrit, sans
rien donner au code (pas de réseau, pas de secret, pas de socket). Les features ne connaissent que
ce port ; l'implémentation concrète (`spool`) est choisie par la composition.

Les plafonds ci-dessous sont **ceux du port** : un travail qui en demande plus est refusé
(`check_job_limits`), et le lanceur du bac les rapplique de son côté sans croire la demande (P6).
Les décalages de `poll` sont des **octets** du journal de sortie encodé en UTF-8."""

from dataclasses import dataclass
from typing import Literal, Protocol

# Plafonds d'un travail : fichiers, octets au total, durée réelle (s) et sortie (octets).
MAX_FILES, MAX_TOTAL_BYTES, MAX_TIMEOUT_S, MAX_OUTPUT_BYTES = 20, 200_000, 15, 65_536


@dataclass(frozen=True)
class SandboxJob:
    """Un travail : les fichiers (chemin relatif -> contenu), le fichier d'entrée, `run` (exécuter)
    ou `check` (seulement vérifier la syntaxe), la durée réelle permise en secondes."""

    run_id: str
    files: dict[str, str]
    entry: str
    kind: Literal["run", "check"]
    timeout_s: int = 10


@dataclass(frozen=True)
class SandboxResult:
    """La fin d'un travail : `done` (terminé, même avec un code de sortie non nul), `timeout`,
    `killed` (annulé, mémoire, processus) ou `error` (le bac n'a pas pu l'exécuter)."""

    status: Literal["done", "timeout", "killed", "error"]
    exit_code: int | None
    duration_ms: int
    truncated: bool


@dataclass(frozen=True)
class SandboxProgress:
    """Ce que `poll` rend : la sortie depuis le décalage demandé, le décalage suivant, et le
    résultat quand le travail est fini (`None` tant qu'il tourne)."""

    output: str
    next_offset: int
    result: SandboxResult | None


class UnknownRun(LookupError):
    """`poll` d'un travail que le bac ne connaît pas (jamais déposé, ou déjà nettoyé)."""


class CodeSandbox(Protocol):
    async def submit(self, job: SandboxJob) -> None:
        """Dépose le travail. Lève `ValueError` s'il dépasse un plafond (`check_job_limits`)."""
        ...

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        """La sortie à partir de `offset` ; lève `UnknownRun` si le travail est inconnu."""
        ...

    async def cancel(self, run_id: str) -> None:
        """Demande l'arrêt du travail ; sans effet s'il est fini ou inconnu."""
        ...

    async def healthy(self) -> bool:
        """Le bac répond-il ? (jamais d'exception : `False` en cas de doute)."""
        ...


def check_job_limits(job: SandboxJob) -> None:
    """Refuse (`ValueError`) un travail hors des plafonds : trop de fichiers ou d'octets, durée
    absente ou trop longue, fichier d'entrée absent, chemin absolu ou remontant."""
    if not 1 <= len(job.files) <= MAX_FILES:
        raise ValueError(f"entre 1 et {MAX_FILES} fichiers attendus")
    if sum(len(text.encode()) for text in job.files.values()) > MAX_TOTAL_BYTES:
        raise ValueError(f"{MAX_TOTAL_BYTES} octets au plus")
    if not 1 <= job.timeout_s <= MAX_TIMEOUT_S:
        raise ValueError(f"durée entre 1 et {MAX_TIMEOUT_S} secondes")
    for name in job.files:
        parts = name.split("/")
        if not name or name.startswith(("/", "\\")) or ".." in parts or "\\" in name:
            raise ValueError("chemin de fichier refusé")
    if job.entry not in job.files:
        raise ValueError("le fichier d'entrée est absent des fichiers")
