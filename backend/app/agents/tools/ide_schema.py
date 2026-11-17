"""Sorties structurées des agents de l'IDE (phase 10, 10.A3) : la note du professeur et l'exercice
du rédacteur d'exercices. Ce sont des sorties de modèle : le nœud les revérifie (le code décide du
type de note, de la plage et de l'empreinte, jamais le modèle)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

NOTE_TEXT_MAX = 3_000
REPLACEMENT_MAX = 4_000
PATH_MAX = 200

TeacherKind = Literal["hint", "explanation", "annotation", "proposal"]
Level = Literal["beginner", "intermediate", "advanced"]


class TeacherNote(BaseModel):
    """Ce que le professeur rend : un indice, une explication, une annotation en marge ou (en
    binôme seulement) une proposition de correction (`replacement` remplace les lignes
    `start_line` à `end_line` de `path`)."""

    kind: TeacherKind
    level: int | None = Field(default=None, ge=1, le=3)
    path: str | None = Field(default=None, max_length=PATH_MAX)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=NOTE_TEXT_MAX)
    replacement: str | None = Field(default=None, max_length=REPLACEMENT_MAX)


class ExerciseDraft(BaseModel):
    """Un exercice écrit par le modèle : l'énoncé, les fichiers de départ (avec les tests) et une
    solution de référence que le code fait passer dans le bac à sable avant de ranger l'exercice.
    `solution` donne les fichiers corrigés (chemin -> contenu) ; elle n'est jamais rangée. Les
    tests de `files` s'imposent à la vérification : la solution ne peut pas les changer."""

    title: str = Field(min_length=3, max_length=120)
    statement: str = Field(min_length=20, max_length=4_000)
    entry: str = Field(default="main.py", min_length=1, max_length=PATH_MAX)
    files: dict[str, str] = Field(min_length=1, max_length=10)
    solution: dict[str, str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def _tests_and_entry(self) -> "ExerciseDraft":
        if not any(name.rsplit("/", 1)[-1].startswith("test_") for name in self.files):
            raise ValueError("l'exercice demande un fichier de tests (test_*.py)")
        if self.entry not in self.files or self.entry not in self.solution:
            raise ValueError("le fichier d'entrée doit être dans les fichiers et la solution")
        return self
