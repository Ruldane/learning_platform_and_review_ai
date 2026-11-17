"""Implémentation du bac à sable par volume d'échange (phase 10, P5 et P6) : le back dépose
`<spool>/jobs/<run_id>.json` ; le lanceur du conteneur `sandbox` (`sandbox/runner.py`, sans réseau
ni socket) l'exécute et rend `<spool>/out/<run_id>.log` (la sortie, 64 Kio au plus) puis
`<run_id>.done.json` (la fin). Annulation : un fichier `<spool>/cancel/<run_id>`. Battement de
coeur : `<spool>/heartbeat` (son âge dit si le bac tourne).

Seule la composition (`app.bootstrap_ide`) importe ce module : les features ne connaissent que le
port `CodeSandbox` (contrat d'import 3). Le dossier d'échange est `2770 root:12345` ; le back y
accède par `group_add: ["12345"]`. Si le bac est arrêté, `submit` lève une `OSError`."""

import asyncio
import json
import os
import secrets
import time
from pathlib import Path
from typing import Literal

from app.providers.sandbox.base import (
    MAX_OUTPUT_BYTES,
    SandboxJob,
    SandboxProgress,
    SandboxResult,
    UnknownRun,
    check_job_limits,
    check_run_id,
)

HEARTBEAT_MAX_AGE_S = 5.0
# Le lanceur borne le journal à `MAX_OUTPUT_BYTES` : le back ne lit jamais plus (plus quatre octets
# pour un caractère coupé), même si le volume contenait un fichier énorme.
MAX_READ_BYTES = MAX_OUTPUT_BYTES + 4
# Taille d'un travail déposé : le lanceur en refuse au-delà (200 000 octets de caractères de
# contrôle font 1,2 Mo une fois échappés en JSON ; même valeur que `MAX_JOB_BYTES` du lanceur).
MAX_JOB_BYTES = 1_500_000
# Un travail resté en file plus longtemps alors que le lanceur ne bat plus : le bac est tombé.
QUEUE_DEAD_S = 60.0
_STATUSES: tuple[Literal["done", "timeout", "killed", "error"], ...] = (
    "done",
    "timeout",
    "killed",
    "error",
)


def _utf8_complete(data: bytes) -> bytes:
    """`data` sans un éventuel caractère UTF-8 coupé à la fin (il sera lu à l'appel suivant)."""
    for cut in range(len(data), max(len(data) - 4, -1), -1):
        try:
            data[:cut].decode("utf-8")
            return data[:cut]
        except UnicodeDecodeError as exc:
            if exc.reason != "unexpected end of data":
                return data
    return data


def _read_result(path: Path) -> SandboxResult | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        status = raw["status"]
        code = raw["exit_code"]
        return SandboxResult(
            status=status if status in _STATUSES else "error",
            exit_code=code if isinstance(code, int) and not isinstance(code, bool) else None,
            duration_ms=int(raw["duration_ms"]),
            truncated=bool(raw["truncated"]),
        )
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError, OSError):
        return SandboxResult(status="error", exit_code=None, duration_ms=0, truncated=False)


class SpoolSandbox:
    """`CodeSandbox` par volume d'échange. Les accès disque sont de petits fichiers, faits dans
    un fil (`asyncio.to_thread`) pour ne jamais bloquer la boucle d'événements."""

    def __init__(self, spool_dir: Path) -> None:
        self._dir = Path(spool_dir)

    def _job(self, run_id: str) -> Path:
        return self._dir / "jobs" / f"{run_id}.json"

    def _log(self, run_id: str) -> Path:
        return self._dir / "out" / f"{run_id}.log"

    def _done(self, run_id: str) -> Path:
        return self._dir / "out" / f"{run_id}.done.json"

    async def submit(self, job: SandboxJob) -> None:
        check_job_limits(job)
        await asyncio.to_thread(self._write_job, job)

    def _write_job(self, job: SandboxJob) -> None:
        if self._log(job.run_id).exists():
            raise ValueError("travail déjà déposé")
        body = {
            "run_id": job.run_id,
            "files": job.files,
            "entry": job.entry,
            "kind": job.kind,
            "timeout_s": job.timeout_s,
        }
        try:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:  # une substitution orpheline n'est pas du texte
            raise ValueError("texte invalide dans les fichiers") from None
        if len(payload) > MAX_JOB_BYTES:
            raise ValueError("travail trop gros")
        tmp = self._dir / "jobs" / f".{job.run_id}.{secrets.token_hex(4)}.tmp"  # un par dépôt
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o660)
        try:
            os.fchmod(fd, 0o660)  # le umask du back (022) retirerait l'écriture au groupe
            os.write(fd, payload)
        finally:
            os.close(fd)
        try:
            os.link(tmp, self._job(job.run_id))  # échoue si présent : deux dépôts ne s'écrasent pas
        except FileExistsError:
            raise ValueError("travail déjà déposé") from None
        finally:
            os.unlink(tmp)

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        try:
            check_run_id(run_id)
        except ValueError:
            raise UnknownRun(run_id) from None
        return await asyncio.to_thread(self._poll, run_id, max(offset, 0))

    def _poll(self, run_id: str, offset: int) -> SandboxProgress:
        result = _read_result(self._done(run_id))  # avant le journal : fin => journal complet
        try:
            with open(self._log(run_id), "rb") as handle:
                handle.seek(offset)
                data = handle.read(MAX_READ_BYTES)
        except FileNotFoundError:
            data = None
        if data is None:
            if result is not None:
                return SandboxProgress(output="", next_offset=offset, result=result)
            return self._queued(run_id, offset)
        if result is None:
            data = _utf8_complete(data)
        return SandboxProgress(
            output=data.decode("utf-8", errors="replace"),
            next_offset=offset + len(data),
            result=result,
        )

    def _queued(self, run_id: str, offset: int) -> SandboxProgress:
        try:
            age = time.time() - self._job(run_id).stat().st_mtime
        except FileNotFoundError:
            raise UnknownRun(run_id) from None
        if age > QUEUE_DEAD_S and not self._beating():
            dead = SandboxResult(status="error", exit_code=None, duration_ms=0, truncated=False)
            return SandboxProgress(output="", next_offset=offset, result=dead)
        return SandboxProgress(output="", next_offset=offset, result=None)

    async def cancel(self, run_id: str) -> None:
        try:
            check_run_id(run_id)
        except ValueError:
            return
        await asyncio.to_thread(self._cancel, run_id)

    def _cancel(self, run_id: str) -> None:
        if self._done(run_id).exists():
            return
        if not (self._job(run_id).exists() or self._log(run_id).exists()):
            return
        marker = self._dir / "cancel" / run_id
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT, 0o660)
        os.fchmod(fd, 0o660)
        os.close(fd)

    def _beating(self) -> bool:
        try:
            age = time.time() - (self._dir / "heartbeat").stat().st_mtime
        except OSError:
            return False
        return age < HEARTBEAT_MAX_AGE_S

    async def healthy(self) -> bool:
        try:
            return await asyncio.to_thread(self._beating)
        except Exception:
            return False
