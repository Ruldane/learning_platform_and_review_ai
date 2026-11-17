"""Schémas de l'IDE Python (phase 10, P1) : définitifs dès 10.P ; un flux ne change jamais la
surface (s'il le faut, il régénère `contracts/openapi.json` et `schema.d.ts` et le dit)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.db.models.ide import (
    ExerciseOrigin,
    NoteAuthor,
    NoteKind,
    NoteStatus,
    Origin,
    RunKind,
    RunStatus,
    TeacherMode,
    TeacherStyle,
)
from app.features.ide.hashing import file_hash
from app.providers.sandbox.base import (
    MAX_FILES,
    MAX_PATH_CHARS,
    MAX_TOTAL_BYTES,
    check_file_name,
)

__all__ = [
    "ExerciseGenerateIn",
    "ExerciseIn",
    "ExerciseOrigin",
    "ExerciseOut",
    "FilesPutIn",
    "NoteAuthor",
    "NoteIn",
    "NoteKind",
    "NoteOut",
    "NoteStatus",
    "Origin",
    "PreferencesIn",
    "PreferencesOut",
    "RunIn",
    "RunKind",
    "RunOut",
    "RunProgress",
    "RunStatus",
    "SessionCreateIn",
    "IdeSessionOut",
    "IdeSessionStarted",
    "SessionSummary",
    "TeachIn",
    "TeachOut",
    "TeacherMode",
    "TeacherStyle",
    "UsageOut",
]

TITLE_MAX = 120
STATEMENT_MAX = 8_000
NOTE_MAX = 4_000
QUESTION_MAX = 2_000
PATH_MAX = MAX_PATH_CHARS

Level = Literal["beginner", "intermediate", "advanced"]
TeachTrigger = Literal["run_error", "run_ok", "question", "hint", "idle"]
SkipReason = Literal["cap_reached", "on_demand", "busy"]


def _check_files(files: dict[str, str]) -> dict[str, str]:
    """Au plus 20 fichiers et 200 000 octets ; chemins relatifs (`check_file_name`)."""
    if len(files) > MAX_FILES:
        raise ValueError("trop de fichiers")
    if sum(len(text.encode()) for text in files.values()) > MAX_TOTAL_BYTES:
        raise ValueError("fichiers trop volumineux")
    for name in files:
        check_file_name(name)
    return files


class ExerciseIn(BaseModel):
    """Un exercice écrit à la main : l'énoncé et, au choix, des fichiers de départ."""

    title: str = Field(min_length=1, max_length=TITLE_MAX)
    statement: str = Field(min_length=1, max_length=STATEMENT_MAX)
    files: dict[str, str] = Field(default_factory=dict)
    entry: str = Field(default="main.py", min_length=1, max_length=PATH_MAX)

    _files = field_validator("files")(_check_files)


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    statement: str
    files: dict[str, str]
    entry: str
    origin: ExerciseOrigin
    topic: str | None
    created_at: datetime


class ExerciseGenerateIn(BaseModel):
    """`topic` : le sujet de l'exercice à faire générer par les agents."""

    topic: str = Field(min_length=1, max_length=300)
    level: Level = "beginner"


class IdeSessionStarted(BaseModel):
    """Le graphe tourne : `session_id` désigne la session d'agents à suivre (en moins de 2 s)."""

    session_id: str


class SessionCreateIn(BaseModel):
    """Ouvre une séance sur un exercice, ou une séance libre (sans `exercise_id`)."""

    exercise_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)


class SessionSummary(BaseModel):
    """`passed` : la séance a eu une vérification (`check`) réussie (`passed_at` : la première)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    exercise_id: str | None
    updated_at: datetime
    passed: bool
    passed_at: datetime | None


class IdeSessionOut(SessionSummary):
    """`file_hashes` : le sha256 de chaque fichier (le `base_hash` que Claude renvoie)."""

    files: dict[str, str]
    entry: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_hashes(self) -> dict[str, str]:
        return {name: file_hash(text) for name, text in self.files.items()}


class FilesPutIn(BaseModel):
    """Enregistre les fichiers de la séance. Interface : remplace tous les fichiers. Claude (MCP,
    interrupteur allumé) : un seul fichier de `files`, les autres sont gardés ; `base_hash` est
    alors obligatoire : le sha256 du contenu actuel de ce fichier (`file_hashes` de la séance ;
    texte vide pour un nouveau fichier). Il est ignoré pour l'interface. `entry` aussi, pour
    Claude."""

    files: dict[str, str]
    entry: str | None = Field(default=None, min_length=1, max_length=PATH_MAX)
    base_hash: str | None = Field(default=None, min_length=64, max_length=64)

    _files = field_validator("files")(_check_files)


class RunIn(BaseModel):
    """`run` exécute `entry` ; `check` lance les tests de l'exercice par pytest dans le bac (code de
    sortie 0 = réussi). `entry` : le fichier d'entrée (celui de la séance par défaut)."""

    kind: RunKind = "run"
    entry: str | None = Field(default=None, min_length=1, max_length=PATH_MAX)


class RunOut(BaseModel):
    """Une exécution déposée (202) : on lit la sortie par `GET /ide/runs/{id}?after=`. `origin` :
    `mcp` quand Claude l'a lancée (la page affiche « lancée par Claude »)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    kind: RunKind
    entry: str
    status: RunStatus
    created_at: datetime
    origin: Origin


class RunProgress(BaseModel):
    """La sortie depuis `after` (octets), le décalage suivant, et la fin quand le bac l'a rendue."""

    id: str
    status: RunStatus
    output: str
    next_offset: int
    exit_code: int | None
    duration_ms: int | None
    truncated: bool


class TeachIn(BaseModel):
    """Ce qui déclenche le professeur : une exécution en erreur (`run_error`) ou réussie
    (`run_ok`), une question (`question`, non vide : 422 sinon), une demande d'indice (`hint`) ou,
    en option, 30 s d'arrêt sur une ligne (`idle`). Jamais à la frappe."""

    trigger: TeachTrigger
    question: str | None = Field(default=None, max_length=QUESTION_MAX)
    file_path: str | None = Field(default=None, max_length=PATH_MAX)
    line: int | None = Field(default=None, ge=1)
    run_id: str | None = None

    @model_validator(mode="after")
    def _question_needed(self) -> "TeachIn":
        if self.trigger == "question" and not (self.question or "").strip():
            raise ValueError("la question est vide")
        return self


class TeachOut(BaseModel):
    """Un seul des trois : `session_id` (le graphe du professeur travaille), `reference_note_id`
    (même erreur au même endroit : renvoi à la note précédente) ou `skipped` (pourquoi rien n'est
    lancé)."""

    session_id: str | None = None
    reference_note_id: str | None = None
    skipped: SkipReason | None = None


class NoteIn(BaseModel):
    """Une note ajoutée à la main ou par Claude : l'auteur vient de l'appelant, jamais du corps.
    Une proposition porte `replacement`, la plage de lignes et `base_hash` : le sha256 hexadécimal
    (minuscules, 64 signes) du contenu du fichier encodé en UTF-8."""

    kind: NoteKind
    content: str = Field(min_length=1, max_length=NOTE_MAX)
    file_path: str | None = Field(default=None, max_length=PATH_MAX)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    replacement: str | None = Field(default=None, max_length=NOTE_MAX)
    base_hash: str | None = Field(default=None, min_length=64, max_length=64)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    kind: NoteKind
    author: NoteAuthor
    author_label: str | None
    origin: Origin  # `mcp` : écrite par Claude (la page affiche « Claude »)
    status: NoteStatus
    file_path: str | None
    line_start: int | None
    line_end: int | None
    content: str
    replacement: str | None
    base_hash: str | None
    reference_note_id: str | None
    level: int | None  # niveau réel d'un indice gradué (1 à 3), vide pour les autres notes
    created_at: datetime


class PreferencesIn(BaseModel):
    """Mode du professeur (`auto` ou sur demande), style (`guide` : indices gradués ; `pair` :
    binôme, annotations en marge et propositions à accepter), minuterie d'inactivité (30 s, en
    option), plafonds de jetons, et l'interrupteur « Claude peut écrire dans mes fichiers »
    (`mcp_can_write_files`, éteint par défaut : seule l'interface le règle, jamais le MCP)."""

    teacher_mode: TeacherMode = "auto"
    teacher_style: TeacherStyle = "guide"
    idle_trigger: bool = False
    mcp_can_write_files: bool = False
    session_cap: int = Field(default=100_000, ge=1_000, le=2_000_000)
    day_cap: int = Field(default=300_000, ge=1_000, le=10_000_000)


class PreferencesOut(PreferencesIn):
    model_config = ConfigDict(from_attributes=True)


class UsageOut(BaseModel):
    """La consommation du professeur : jetons de la séance et du jour, leurs plafonds, et si le
    professeur est passé en mode « sur demande » (plafond atteint ou choix)."""

    session_tokens: int
    day_tokens: int
    session_cap: int
    day_cap: int
    mode_on_demand: bool
