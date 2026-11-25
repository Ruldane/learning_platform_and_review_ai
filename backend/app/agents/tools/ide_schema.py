"""Structured outputs of the IDE agents (phase 10, 10.A3): the teacher's note and the exercise
of the exercise writer. They are model outputs: the node re-checks them (the code decides the
note type, the range and the fingerprint, never the model)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

NOTE_TEXT_MAX = 3_000
REPLACEMENT_MAX = 4_000
PATH_MAX = 200

TeacherKind = Literal["hint", "explanation", "annotation", "proposal"]
Level = Literal["beginner", "intermediate", "advanced"]


class TeacherNote(BaseModel):
    """What the teacher returns: a hint, an explanation, a margin annotation or (in pair
    mode only) a correction proposal (`replacement` replaces the lines `start_line` to
    `end_line` of `path`)."""

    kind: TeacherKind
    level: int | None = Field(default=None, ge=1, le=3)
    path: str | None = Field(default=None, max_length=PATH_MAX)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=NOTE_TEXT_MAX)
    replacement: str | None = Field(default=None, max_length=REPLACEMENT_MAX)


class ExerciseDraft(BaseModel):
    """An exercise written by the model: the statement, the starter files (with the tests) and a
    reference solution that the code runs in the sandbox before storing the exercise.
    `solution` gives the corrected files (path -> content); it is never stored. The tests of
    `files` prevail at verification: the solution cannot change them."""

    title: str = Field(min_length=3, max_length=120)
    statement: str = Field(min_length=20, max_length=4_000)
    entry: str = Field(default="main.py", min_length=1, max_length=PATH_MAX)
    files: dict[str, str] = Field(min_length=1, max_length=10)
    solution: dict[str, str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def _tests_and_entry(self) -> "ExerciseDraft":
        if not any(name.rsplit("/", 1)[-1].startswith("test_") for name in self.files):
            raise ValueError("the exercise needs a test file (test_*.py)")
        if self.entry not in self.files or self.entry not in self.solution:
            raise ValueError("the entry file must be among the files and the solution")
        return self
