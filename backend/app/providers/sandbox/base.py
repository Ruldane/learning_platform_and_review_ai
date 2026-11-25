"""The `CodeSandbox` port (phase 10, P5 to P7): run code that January or Claude wrote, without
giving the code anything (no network, no secret, no socket). The features only know
this port; the concrete implementation (`spool`) is chosen by the composition.

The caps below are **the port's**: a job that asks for more is refused
(`check_job_limits`), and the sandbox launcher applies them again on its side without trusting the
request (P6). The `poll` offsets are **bytes** of the output log encoded in UTF-8."""

import re
from dataclasses import dataclass
from typing import Literal, Protocol

# Caps of a job: files, total bytes, real duration (s) and output (bytes).
MAX_FILES, MAX_TOTAL_BYTES, MAX_TIMEOUT_S, MAX_OUTPUT_BYTES = 20, 200_000, 15, 65_536
MAX_INPUT_CHUNK_BYTES, MAX_INPUT_BYTES = 4_096, 65_536
MAX_NOTEBOOK_SOURCE_BYTES = 65_536
# Length of a file path (and of the entry file), in the database as in the schemas.
MAX_PATH_CHARS = 200

# A job identifier becomes a file name of the sandbox: uuid in 32 hexadecimals or uuid4
# as text (with dashes), nothing else.
_RUN_ID = re.compile(r"[0-9a-f]{32}|[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_DRIVE = re.compile(r"[A-Za-z]:")
SandboxKind = Literal["run", "check", "terminal", "notebook"]


@dataclass(frozen=True)
class SandboxJob:
    """A job: the files (relative path -> content), the entry file, `run` (runs
    `entry`) or `check` (runs the exercise's tests with `python -m pytest -q` on the job's test
    files; exit code 0 = passed), the real duration allowed in seconds."""

    run_id: str
    files: dict[str, str]
    entry: str
    kind: SandboxKind
    timeout_s: int = 10
    source: str | None = None
    model_user: str | None = None


@dataclass(frozen=True)
class SandboxResult:
    """The end of a job: `done` (finished, even with a non-zero exit code), `timeout`,
    `killed` (cancelled, memory, processes) or `error` (the sandbox could not run it)."""

    status: Literal["done", "timeout", "killed", "error"]
    exit_code: int | None
    duration_ms: int
    truncated: bool


@dataclass(frozen=True)
class SandboxProgress:
    """What `poll` returns: the output since the requested offset, the next offset, and the
    result when the job is finished (`None` while it runs)."""

    output: str
    next_offset: int
    result: SandboxResult | None


class UnknownRun(LookupError):
    """`poll` of a job that the sandbox does not know (never submitted, or already cleaned up)."""


class CodeSandbox(Protocol):
    async def submit(self, job: SandboxJob) -> None:
        """Submits the job. Raises `ValueError` if it exceeds a cap (`check_job_limits`)."""
        ...

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        """The output from `offset`; raises `UnknownRun` if the job is unknown."""
        ...

    async def cancel(self, run_id: str) -> None:
        """Asks for the job to stop; no effect if it is finished or unknown."""
        ...

    async def write_input(self, run_id: str, data: bytes) -> None:
        """Sends a bounded input to the interactive job. Raises `UnknownRun` if it is finished."""
        ...

    async def healthy(self) -> bool:
        """Does the sandbox answer? (never an exception: `False` when in doubt)."""
        ...


def _size(text: str) -> int:
    """The bytes of a text in UTF-8; `ValueError` for an orphan surrogate."""
    try:
        return len(text.encode())
    except UnicodeEncodeError:
        raise ValueError("invalid text (UTF-8)") from None


def check_run_id(run_id: str) -> None:
    """Refuses (`ValueError`) an identifier that is not a uuid (32 hexadecimals, or uuid4 as
    text): it serves as a file name for the sandbox, never a path."""
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("job identifier refused")


def check_file_name(name: str) -> None:
    """Refuses (`ValueError`) a file path that is empty, too long, absolute (slash, drive),
    going up (`..`), with an empty or `.` segment (`a//b`, `a/./b`, `a/`), with a backslash
    or a null."""
    if not name or len(name) > MAX_PATH_CHARS or "\\" in name or "\x00" in name:
        raise ValueError("file path refused")
    if name.startswith("/") or _DRIVE.match(name):
        raise ValueError("file path refused")
    if any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("file path refused")


def check_job_limits(job: SandboxJob) -> None:
    """Refuses (`ValueError`) a job outside the caps: identifier that is not a uuid,
    too many files or bytes, missing or too long duration, refused path (`check_file_name`),
    missing entry file."""
    check_run_id(job.run_id)
    if not 1 <= len(job.files) <= MAX_FILES:
        raise ValueError(f"between 1 and {MAX_FILES} files expected")
    if (job.kind == "notebook") != (job.source is not None):
        raise ValueError("invalid cell source")
    source_size = _size(job.source or "")
    if source_size > MAX_NOTEBOOK_SOURCE_BYTES:
        raise ValueError("cell source too long")
    if sum(_size(text) for text in job.files.values()) + source_size > MAX_TOTAL_BYTES:
        raise ValueError(f"{MAX_TOTAL_BYTES} bytes at most")
    if not 1 <= job.timeout_s <= MAX_TIMEOUT_S:
        raise ValueError(f"duration between 1 and {MAX_TIMEOUT_S} seconds")
    for name in job.files:
        check_file_name(name)
    check_file_name(job.entry)
    if job.entry not in job.files:
        raise ValueError("the entry file is missing from the files")
