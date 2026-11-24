import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

Status = Literal["draft", "confirmed", "open", "closed", "accepted"]
_DraftText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]
_PORTABLE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")


class CreateContribution(BaseModel):
    program_id: str = Field(min_length=1, max_length=64)
    repository: str = Field(min_length=3, max_length=140)
    issue_number: int = Field(ge=1, lt=10**9)


class PublicationIn(BaseModel):
    confirm: Literal[True]
    author: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
    head: str = Field(min_length=1, max_length=100)
    title: _DraftText = Field(max_length=120)
    body: _DraftText = Field(max_length=1400)

    @field_validator("confirm", mode="before")
    @classmethod
    def confirmation(cls, value: object) -> bool:
        if value is not True:
            raise ValueError("The GitHub preparation must be confirmed.")
        return True

    @field_validator("head")
    @classmethod
    def branch(cls, value: str) -> str:
        if (
            not _PORTABLE_REF.fullmatch(value)
            or ".." in value
            or any(
                not part or part.startswith(".") or part.endswith(".lock")
                for part in value.split("/")
            )
            or value.endswith(".")
        ):
            raise ValueError("Enter a valid Git branch.")
        return value


class PullIn(BaseModel):
    url: str = Field(min_length=1, max_length=350)


class SuggestedIssue(BaseModel):
    repository: str
    number: int
    title: str
    body: str
    url: str
    skills: list[str]


class SuggestionsOut(BaseModel):
    chapter: str | None
    items: list[SuggestedIssue]


class ContributionOut(BaseModel):
    id: str
    program_id: str
    chapter: str
    issue: SuggestedIssue
    status: Status
    base: str
    publication_url: str | None = None
    pull_url: str | None = None
    cv_line: str | None = None
