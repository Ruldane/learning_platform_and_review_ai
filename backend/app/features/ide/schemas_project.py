"""Commandes ciblées du projet et vue des onglets."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.providers.sandbox.base import MAX_FILES, MAX_PATH_CHARS, MAX_TOTAL_BYTES

ProjectPath = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PATH_CHARS)]


class ProjectEditIn(BaseModel):
    path: ProjectPath
    version: int = Field(ge=0)


class ProjectFileCreate(ProjectEditIn):
    content: str = Field(default="", max_length=MAX_TOTAL_BYTES)


class ProjectFileRename(ProjectEditIn):
    destination: ProjectPath


class ProjectFileRemove(ProjectEditIn):
    replacement_entry: ProjectPath | None = None


class ProjectTabsState(BaseModel):
    open_paths: list[ProjectPath] = Field(max_length=MAX_FILES)
    active_path: ProjectPath | None = None
