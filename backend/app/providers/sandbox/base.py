"""Le port `CodeSandbox` (phase 10, P5 à P7) : exécuter du code que January ou Claude a écrit, sans
rien donner au code (pas de réseau, pas de secret, pas de socket). Les features ne connaissent que
ce port ; l'implémentation concrète (`spool`) est choisie par la composition.

Les plafonds ci-dessous sont **ceux du port** : un travail qui en demande plus est refusé
(`check_job_limits`), et le lanceur du bac les rapplique de son côté sans croire la demande (P6).
Les décalages de `poll` sont des **octets** du journal de sortie encodé en UTF-8."""

import re
from dataclasses import dataclass
from typing import Literal, Protocol

# Plafonds d'un travail : fichiers, octets au total, durée réelle (s) et sortie (octets).
MAX_FILES, MAX_TOTAL_BYTES, MAX_TIMEOUT_S, MAX_OUTPUT_BYTES = 20, 200_000, 15, 65_536
MAX_INPUT_CHUNK_BYTES, MAX_INPUT_BYTES = 4_096, 65_536
MAX_NOTEBOOK_SOURCE_BYTES = 65_536
# Longueur d'un chemin de fichier (et du fichier d'entrée), en base comme dans les schémas.
MAX_PATH_CHARS = 200

# Un identifiant de travail devient un nom de fichier du bac : uuid en 32 hexadécimaux ou uuid4
# en texte (avec tirets), rien d'autre.
_RUN_ID = re.compile(r"[0-9a-f]{32}|[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_DRIVE = re.compile(r"[A-Za-z]:")
SandboxKind = Literal["run", "check", "terminal", "notebook"]


@dataclass(frozen=True)
class SandboxJob:
    """Un travail : les fichiers (chemin relatif -> contenu), le fichier d'entrée, `run` (exécute
    `entry`) ou `check` (lance les tests de l'exercice par `python -m pytest -q` sur les fichiers de
    test du travail ; code de sortie 0 = réussi), la durée réelle permise en secondes."""

    run_id: str
    files: dict[str, str]
    entry: str
    kind: SandboxKind
    timeout_s: int = 10
    source: str | None = None
    model_user: str | None = None


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

    async def write_input(self, run_id: str, data: bytes) -> None:
        """Transmet une entrée bornée au travail interactif. Lève `UnknownRun` s'il est fini."""
        ...

    async def healthy(self) -> bool:
        """Le bac répond-il ? (jamais d'exception : `False` en cas de doute)."""
        ...


def _size(text: str) -> int:
    """Les octets d'un texte en UTF-8 ; `ValueError` pour une substitution orpheline."""
    try:
        return len(text.encode())
    except UnicodeEncodeError:
        raise ValueError("texte invalide (UTF-8)") from None


def check_run_id(run_id: str) -> None:
    """Refuse (`ValueError`) un identifiant qui n'est pas un uuid (32 hexadécimaux, ou uuid4 en
    texte) : il sert de nom de fichier au bac, jamais un chemin."""
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("identifiant de travail refusé")


def check_file_name(name: str) -> None:
    """Refuse (`ValueError`) un chemin de fichier vide, trop long, absolu (barre, lecteur),
    remontant (`..`), à segment vide ou `.` (`a//b`, `a/./b`, `a/`), avec barre inverse ou nul."""
    if not name or len(name) > MAX_PATH_CHARS or "\\" in name or "\x00" in name:
        raise ValueError("chemin de fichier refusé")
    if name.startswith("/") or _DRIVE.match(name):
        raise ValueError("chemin de fichier refusé")
    if any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("chemin de fichier refusé")


def check_job_limits(job: SandboxJob) -> None:
    """Refuse (`ValueError`) un travail hors des plafonds : identifiant qui n'est pas un uuid,
    trop de fichiers ou d'octets, durée absente ou trop longue, chemin refusé (`check_file_name`),
    fichier d'entrée absent."""
    check_run_id(job.run_id)
    if not 1 <= len(job.files) <= MAX_FILES:
        raise ValueError(f"entre 1 et {MAX_FILES} fichiers attendus")
    if (job.kind == "notebook") != (job.source is not None):
        raise ValueError("source de cellule invalide")
    source_size = _size(job.source or "")
    if source_size > MAX_NOTEBOOK_SOURCE_BYTES:
        raise ValueError("source de cellule trop longue")
    if sum(_size(text) for text in job.files.values()) + source_size > MAX_TOTAL_BYTES:
        raise ValueError(f"{MAX_TOTAL_BYTES} octets au plus")
    if not 1 <= job.timeout_s <= MAX_TIMEOUT_S:
        raise ValueError(f"durée entre 1 et {MAX_TIMEOUT_S} secondes")
    for name in job.files:
        check_file_name(name)
    check_file_name(job.entry)
    if job.entry not in job.files:
        raise ValueError("le fichier d'entrée est absent des fichiers")
