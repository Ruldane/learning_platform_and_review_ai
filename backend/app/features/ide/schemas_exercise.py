"""Schémas des exercices de l'IDE (phase 10) : écrits à la main, retouchés, lus, ou générés par les
agents. Réexportés par `app.features.ide.schemas`."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models.ide import ExerciseOrigin
from app.providers.sandbox.base import (
    MAX_FILES,
    MAX_PATH_CHARS,
    MAX_TOTAL_BYTES,
    check_file_name,
)

TITLE_MAX = 120
STATEMENT_MAX = 8_000
PATH_MAX = MAX_PATH_CHARS

Level = Literal["beginner", "intermediate", "advanced"]


def check_files(files: dict[str, str]) -> dict[str, str]:
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

    _files = field_validator("files")(check_files)


class ExercisePatch(BaseModel):
    """Retouche d'un exercice : les champs donnés remplacent ceux de l'exercice (`files` remplace
    tous ses fichiers, énoncé de départ et tests pytest compris) ; l'origine ne change pas."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    statement: str | None = Field(default=None, min_length=1, max_length=STATEMENT_MAX)
    files: dict[str, str] | None = None
    entry: str | None = Field(default=None, min_length=1, max_length=PATH_MAX)

    @field_validator("files")
    @classmethod
    def _files(cls, files: dict[str, str] | None) -> dict[str, str] | None:
        return None if files is None else check_files(files)

    @model_validator(mode="after")
    def _something(self) -> "ExercisePatch":
        if (self.title, self.statement, self.files, self.entry) == (None, None, None, None):
            raise ValueError("rien à changer")
        return self


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
