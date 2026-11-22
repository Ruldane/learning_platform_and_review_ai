"""Le travail reçu par le lanceur (phase 10, 10.A1) : plafonds, validation, fichiers, commande et
environnement du code. Stdlib seule : l'image du bac n'a que Python et pytest.

Règle d'or : **le lanceur ne croit jamais le travail**. Les plafonds (`Limits`) sont des
constantes ; le travail ne peut que demander moins (durée). Le code tourne avec un environnement
**vide** (`PATH`, `HOME`, `PYTHONDONTWRITEBYTECODE`), jamais celui du lanceur."""

import json
import os
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MIB = 1024 * 1024
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
MAX_NAME, MAX_PART, MAX_DEPTH = 200, 100, 8
MAX_NOTEBOOK_SOURCE_BYTES = 65_536
_OWNER = re.compile(r"[A-Za-z0-9_-]{1,36}")


@dataclass(frozen=True)
class Limits:
    """Les plafonds du lanceur (constantes ; jamais lus dans le travail)."""

    uid: int = 20000
    gid: int = 20000
    cpu_s: int = 10
    memory_bytes: int = 256 * MIB
    wall_default_s: int = 10
    wall_max_s: int = 15
    processes: int = 32
    file_bytes: int = 8 * MIB
    open_files: int = 256
    output_bytes: int = 65_536
    max_files: int = 20
    max_total_bytes: int = 200_000


@dataclass(frozen=True)
class SandboxResult:
    """La fin d'un travail (mêmes champs que `app.providers.sandbox.base.SandboxResult`)."""

    status: Literal["done", "timeout", "killed", "error"]
    exit_code: int | None
    duration_ms: int
    truncated: bool


@dataclass(frozen=True)
class RunEnv:
    """Où et comment lancer : dossiers, interpréteur, et si l'on change d'identité (`drop`,
    faux seulement dans les tests unitaires, qui ne tournent pas en root du bac)."""

    spool: Path = Path("/spool")
    work: Path = Path("/work")
    python: str = sys.executable
    drop: bool = True
    clean_roots: tuple[str, ...] = ("/tmp", "/dev/shm", "/dev/mqueue")
    tick: Callable[[], None] = field(default=lambda: None)
    stop: Callable[[], bool] = field(default=lambda: False)


class Unsafe(BaseException):
    """Le bac n'est plus sûr (processus survivant, nettoyage échoué, processus qui ne meurt pas) :
    plus aucun travail n'est servi. Le lanceur écrit une fin `error` puis s'arrête (code 70) ;
    Compose le relance (`restart: on-failure`) avec un conteneur neuf. Volontairement hors de
    `Exception` : aucun `except Exception` ne l'avale."""


class JobRefused(ValueError):
    """Le travail est refusé (message en français, écrit dans le journal de sortie)."""


@dataclass(frozen=True)
class Job:
    run_id: str
    files: dict[str, str]
    entry: str
    kind: Literal["run", "check", "terminal", "notebook"]
    wall_s: int
    source: str | None = None
    model_user: str | None = None


def clamp_timeout(raw: object, limits: Limits) -> int:
    """La durée réelle : celle demandée, ramenée entre 1 s et le plafond ; défaut si absente."""
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return limits.wall_default_s
    return max(1, min(int(raw), limits.wall_max_s))


def _check_name(name: object) -> str:
    if not isinstance(name, str) or not name or len(name) > MAX_NAME:
        raise JobRefused("nom de fichier refusé")
    parts = name.split("/")
    if len(parts) > MAX_DEPTH or any(
        not p or p in {".", ".."} or len(p) > MAX_PART or "\\" in p or "\0" in p for p in parts
    ):
        raise JobRefused(f"chemin de fichier refusé : {name[:60]!r}")
    return name


def validate_job(job: object, limits: Limits) -> Job:
    """Vérifie le travail reçu ; lève `JobRefused`. Aucun autre champ n'est lu."""
    if not isinstance(job, dict):
        raise JobRefused("travail illisible")
    run_id, files, entry = job.get("run_id"), job.get("files"), job.get("entry")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise JobRefused("identifiant de travail refusé")
    if not isinstance(files, dict) or not 1 <= len(files) <= limits.max_files:
        raise JobRefused(f"entre 1 et {limits.max_files} fichiers attendus")
    clean: dict[str, str] = {}
    for name, text in files.items():
        if not isinstance(text, str):
            raise JobRefused("contenu de fichier refusé")
        try:
            clean[_check_name(name)] = text
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise JobRefused("contenu de fichier refusé") from exc
    source = job.get("source")
    kind = job.get("kind")
    if kind not in ("run", "check", "terminal", "notebook"):
        raise JobRefused("nature du travail refusée")
    if (kind == "notebook" and not isinstance(source, str)) or (
        kind != "notebook" and source is not None
    ):
        raise JobRefused("source de cellule invalide")
    source_text = source if isinstance(source, str) else None
    try:
        source_size = len(source_text.encode("utf-8")) if source_text is not None else 0
    except UnicodeEncodeError:
        raise JobRefused("source de cellule illisible") from None
    if source_size > MAX_NOTEBOOK_SOURCE_BYTES:
        raise JobRefused("source de cellule trop longue")
    if sum(len(t.encode("utf-8")) for t in clean.values()) + source_size > limits.max_total_bytes:
        raise JobRefused(f"{limits.max_total_bytes} octets au plus")
    if not isinstance(entry, str) or entry not in clean:
        raise JobRefused("le fichier d'entrée est absent des fichiers")
    owner = job.get("model_user")
    model_user = owner if isinstance(owner, str) and _OWNER.fullmatch(owner) else None
    return Job(
        run_id,
        clean,
        entry,
        kind,
        clamp_timeout(job.get("timeout_s"), limits),
        source_text,
        model_user if kind != "check" else None,
    )


def _chown(path: str, limits: Limits, env: RunEnv) -> None:
    if env.drop:
        os.chown(path, limits.uid, limits.gid)


def materialize(job: Job, workdir: Path, limits: Limits, env: RunEnv) -> None:
    """Crée `workdir` (neuf : un dossier existant est refusé) et y écrit les fichiers, puis le
    donne à l'uid du code. Le lanceur en reste propriétaire pendant l'écriture : aucun lien
    symbolique du code n'existe encore."""
    os.mkdir(workdir, 0o700)
    try:
        _write_files(job, workdir)
        for path in [*workdir.rglob("*"), workdir]:
            _chown(str(path), limits, env)
    except BaseException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


def _write_files(job: Job, workdir: Path) -> None:
    for name, text in job.files.items():
        target = workdir
        for part in name.split("/")[:-1]:
            target = target / part
            try:
                os.mkdir(target, 0o700)
            except FileExistsError:
                if not target.is_dir() or target.is_symlink():
                    raise JobRefused("fichiers en conflit") from None
        path = workdir / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))


def is_test_file(name: str) -> bool:
    base = name.rsplit("/", 1)[-1]
    return base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))


def build_command(job: Job, python: str) -> list[str]:
    """`run` : exécute le fichier d'entrée. `check` : lance les tests de l'exercice par pytest
    (fichiers `test_*.py` ou `*_test.py` du travail), sans cache ni fichier de configuration."""
    if job.kind == "notebook":
        return [python, "-X", "utf8", "-u", "-s", "-c", job.source or ""]
    if job.kind == "check":
        tests = sorted(n for n in job.files if is_test_file(n))
        return [
            python,
            "-X",
            "utf8",
            "-s",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--rootdir=.",
            "-c",
            "/dev/null",
            *tests,
        ]
    return [python, "-X", "utf8", "-u", "-s", job.entry]


def build_env(workdir: Path) -> dict[str, str]:
    """L'environnement du code : trois variables, aucune venue du lanceur ni du travail."""
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(workdir),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def job_from_json(raw: bytes) -> dict[str, object]:
    """Lit un travail JSON ; toute erreur devient `JobRefused`."""
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise JobRefused("travail illisible") from exc
    if not isinstance(value, dict):
        raise JobRefused("travail illisible")
    return value
