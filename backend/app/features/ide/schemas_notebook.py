"""Reading, editing and running a Python notebook in the project."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.features.ide.schemas_project import ProjectPath
from app.providers.sandbox.base import MAX_TOTAL_BYTES

MAX_NOTEBOOK_CELLS = 100
CellId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class NotebookCellIn(BaseModel):
    id: CellId
    kind: Literal["code", "markdown", "raw"]
    source: str = Field(max_length=MAX_TOTAL_BYTES)


class NotebookCellOut(NotebookCellIn):
    output: str | None = None
    execution_count: int | None = None


class NotebookPut(BaseModel):
    path: ProjectPath
    version: int = Field(ge=0)
    cells: list[NotebookCellIn] = Field(max_length=MAX_NOTEBOOK_CELLS)


class NotebookView(BaseModel):
    path: ProjectPath
    files_version: int
    cells: list[NotebookCellOut]
    active_run_id: str | None = None


class NotebookRunIn(BaseModel):
    path: ProjectPath
    cell_id: CellId
    include_previous: bool = False
