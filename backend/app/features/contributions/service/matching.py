import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.skills import normalize_skill_name
from app.providers.github.base import GithubIssue, RepoRef

_BEGINNER = frozenset({"good first issue", "beginner", "easy", "first contribution"})


@dataclass(frozen=True)
class Suggestion:
    repo: RepoRef
    issue: GithubIssue
    skills: tuple[str, ...]


def _beginner(labels: tuple[str, ...]) -> bool:
    return any(normalize_skill_name(label.replace("-", " ")) in _BEGINNER for label in labels)


def _matched_skills(issue: GithubIssue, skills: Sequence[str]) -> tuple[str, ...]:
    text = normalize_skill_name(" ".join((issue.title, issue.body, *issue.labels)))
    return tuple(
        name
        for name in dict.fromkeys(skills)
        if (norm := normalize_skill_name(name))
        and re.search(rf"(?<!\w){re.escape(norm)}(?!\w)", text)
    )


def rank_issues(
    repo: RepoRef, issues: Sequence[GithubIssue], skills: Sequence[str]
) -> list[Suggestion]:
    """First contributions with at least one skill matching the chapter."""
    ranked = [
        Suggestion(repo, issue, matched)
        for issue in issues
        if _beginner(issue.labels) and (matched := _matched_skills(issue, skills))
    ]
    return sorted(ranked, key=lambda item: (-len(item.skills), item.issue.number))
