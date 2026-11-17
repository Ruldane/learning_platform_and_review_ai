"""Port de l'IDE Python (phase 10, 10.A3). `app.agents` n'importe aucune feature (contrat 6) : il
décrit ici ce dont les parcours `ide_teacher` et `ide_exercise` ont besoin ; la feature `ide`
l'implémente (`AgentIdeStore`).

Le code de January, la sortie de ses exécutions et l'énoncé d'un exercice sont des données : jamais
journalisés. Les écritures passent par le même service que celles de Claude (`IdeService`), sous
l'appelant interne « professor » : mêmes validations, mêmes notes.

- `teacher_inputs` : lecture seule (séance, dernière exécution, notes, style).
- `save_note` : range la note du professeur ; `None` si le code a changé entre-temps (la
  proposition est périmée, ou la plage n'existe plus) : rien n'est rangé.
- `verify` : fait passer les tests d'un exercice dans le bac à sable (jamais ici, jamais en
  processus) ; `save_exercise` range l'exercice vérifié."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.ide_schema import ExerciseDraft, TeacherNote
from app.core.errors import AppError

Style = Literal["guide", "pair"]


@dataclass(frozen=True)
class RunView:
    """La dernière exécution : sortie complète (64 Kio au plus), signature de son erreur."""

    id: str
    kind: str
    status: str
    exit_code: int | None
    output: str
    error_signature: str | None


@dataclass(frozen=True)
class NoteView:
    id: str
    kind: str
    author: str
    level: int | None
    file_path: str | None
    line_start: int | None
    text: str
    error_key: str | None


@dataclass(frozen=True)
class TeachInputs:
    title: str
    statement: str | None  # l'énoncé de l'exercice (`None` : séance libre)
    files: dict[str, str]
    entry: str
    passed: bool
    style: Style
    run: RunView | None
    notes: list[NoteView] = field(default_factory=list)  # les plus anciennes d'abord


@dataclass(frozen=True)
class Verification:
    """La réponse du bac à sable à une vérification : `passed` si les tests passent (code 0)."""

    passed: bool
    status: str
    output: str


class IdeStore(Protocol):
    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs: ...

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None: ...

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification: ...

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str: ...


def ide_unavailable() -> AppError:
    return AppError("ide_unavailable", "L'IDE n'est pas branché sur ce moteur.", 503)


class _NoIde:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs:
        raise ide_unavailable()

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None:
        raise ide_unavailable()

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification:
        raise ide_unavailable()

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str:
        raise ide_unavailable()


NO_IDE: IdeStore = _NoIde()
