"""The `cv_compose` operations on CV content: find a line by the fact it rewords, remove,
rewrite, add at its place in the profile, move a section. Each operation returns true if it
wrote something, false if its target cannot be found."""

import re
from collections.abc import Callable
from typing import get_args

from app.agents.tools.cv_schema import (
    CvContent,
    CvEntry,
    CvLine,
    CvSection,
    MasterProfileData,
    SectionKey,
    facts_of,
)
from app.agents.tools.review_schema import Proposal, section_of

# Titles of the sections created by the code: French on purpose, like the CVs and profiles of
# this deployment (the ATS checks and `committee_schema` accept the English headings as well).
SECTION_TITLES: dict[SectionKey, str] = {
    "summary": "Profil",
    "experience": "Expériences",
    "education": "Formation",
    "skills": "Compétences",
    "projects": "Projets",
    "languages": "Langues",
    "links": "Liens",
}
_CANONICAL: tuple[str, ...] = get_args(SectionKey)
_CHILD = re.compile(r"^([xfp]\d+)[ad]\d+$")
_ENTRY = re.compile(r"^[xfp]\d+$")
_LAST = 10**9


def period(start: str | None, end: str | None) -> str | None:
    return " – ".join(part for part in (start, end) if part) or None


def heads(profile: MasterProfileData, facts: dict[str, str]) -> dict[str, CvEntry]:
    """An entry with no lines per experience, education and project (`fact_id` = its id)."""
    out: dict[str, CvEntry] = {}
    for x in profile.experiences:
        if x.id in facts:  # a fact without an identifier does not exist for the CV
            out[x.id] = CvEntry(
                heading=facts[x.id],
                subheading=x.location,
                dates=period(x.start, x.end),
                fact_id=x.id,
            )
    for e in profile.education:
        if e.id in facts:
            out[e.id] = CvEntry(heading=facts[e.id], dates=period(e.start, e.end), fact_id=e.id)
    for p in profile.projects:
        if p.id in facts:
            out[p.id] = CvEntry(heading=p.name, fact_id=p.id)
    return out


def _insert[T](seq: list[T], item: T, rank_of: Callable[[T], int], rank: int) -> None:
    """Inserts `item` before the first element of greater rank (the profile's order)."""
    seq.insert(next((n for n, other in enumerate(seq) if rank_of(other) > rank), len(seq)), item)


class Composer:
    """A CV content (copy of `base`) to which changes are applied one by one."""

    def __init__(self, base: CvContent, profile: MasterProfileData) -> None:
        self.content = base.model_copy(deep=True)
        self.facts = facts_of(profile)
        self.heads = heads(profile, self.facts)
        self.rank = {fact_id: n for n, fact_id in enumerate(self.facts)}
        self.title_id = profile.title.id if profile.title is not None else ""

    def apply(self, p: Proposal) -> bool:
        operations = {
            "remove": self._remove,
            "rewrite": self._rewrite,
            "add": self._add,
            "move": self._move,
        }
        written = operations[p.action](p)
        self.content.sections = [s for s in self.content.sections if s.entries or s.items]
        return written

    def _rank_of(self, fact_id: str | None) -> int:
        return self.rank.get(fact_id or "", _LAST)

    def _line_rank(self, line: CvLine) -> int:
        return self._rank_of(line.fact_ids[0] if line.fact_ids else None)

    def _fact_ids(self, p: Proposal) -> list[str]:
        """`target` then the cited facts known to the profile, without duplicates."""
        ids = dict.fromkeys(i for i in (p.target, *p.fact_ids) if i and i in self.facts)
        return list(ids)

    def _entry(self, fact_id: str) -> tuple[CvSection, CvEntry] | None:
        for section in self.content.sections:
            for entry in section.entries:
                if entry.fact_id == fact_id:
                    return section, entry
        return None

    def _line(self, fact_id: str) -> tuple[list[CvLine], CvLine] | None:
        for section in self.content.sections:
            holders = [section.items, *(entry.lines for entry in section.entries)]
            for lines in holders:
                for line in lines:
                    if line.fact_ids and line.fact_ids[0] == fact_id:
                        return lines, line
        return None

    def _is_headline(self, fact_id: str) -> bool:
        return bool(self.title_id) and fact_id == self.title_id

    def _section(self, key: SectionKey) -> CvSection:
        """The section `key`, created at its usual place if the content has none."""
        for section in self.content.sections:
            if section.key == key:
                return section
        created = CvSection(key=key, title=SECTION_TITLES[key])
        _insert(
            self.content.sections,
            created,
            lambda s: _CANONICAL.index(s.key),
            _CANONICAL.index(key),
        )
        return created

    def _remove(self, p: Proposal) -> bool:
        target = p.target or ""
        if self._is_headline(target) and self.content.headline is not None:
            self.content.headline = None
            return True
        if (entry := self._entry(target)) is not None:
            entry[0].entries.remove(entry[1])
            return True
        if (line := self._line(target)) is not None:
            line[0].remove(line[1])
            return True
        return False

    def _rewrite(self, p: Proposal) -> bool:
        target = p.target or ""
        after = p.after.strip()
        if not after or target not in self.facts:
            return False
        if self._is_headline(target) and self.content.headline is not None:
            self.content.headline = after
            return True
        if (entry := self._entry(target)) is not None:
            entry[1].heading = after
            return True
        if (line := self._line(target)) is not None:
            line[1].text = after
            line[1].fact_ids = self._fact_ids(p)
            return True
        return False

    def _add(self, p: Proposal) -> bool:
        target = p.target or ""
        after = p.after.strip()
        if not after or target not in self.facts or section_of(target) is None:
            return False
        if self._entry(target) or self._line(target):
            return False
        if self._is_headline(target):
            if self.content.headline is not None:
                return False
            self.content.headline = after
            return True
        key = section_of(target)
        if key is None:
            return False
        if _ENTRY.match(target):
            return self._add_entry(key, target, after)
        if (child := _CHILD.match(target)) is not None:
            return self._add_child(key, child.group(1), target, after, p)
        line = CvLine(text=after, fact_ids=self._fact_ids(p))
        items = self._section(key).items
        _insert(items, line, self._line_rank, self._rank_of(target))
        return True

    def _add_entry(self, key: SectionKey, target: str, heading: str) -> bool:
        head = self.heads.get(target)
        if head is None:
            return False
        entry = head.model_copy(update={"heading": heading})
        entries = self._section(key).entries
        _insert(entries, entry, lambda e: self._rank_of(e.fact_id), self._rank_of(target))
        return True

    def _add_child(self, key: SectionKey, parent: str, target: str, text: str, p: Proposal) -> bool:
        """An achievement or a detail: in its parent's entry, created with its own facts
        only (role, company, dates) if the original CV did not have it."""
        found = self._entry(parent)
        if found is None:
            head = self.heads.get(parent)
            if head is None:
                return False
            entries = self._section(key).entries
            _insert(entries, head, lambda e: self._rank_of(e.fact_id), self._rank_of(parent))
            entry = head
        else:
            entry = found[1]
        line = CvLine(text=text, fact_ids=self._fact_ids(p))
        _insert(entry.lines, line, self._line_rank, self._rank_of(target))
        return True

    def _move(self, p: Proposal) -> bool:
        sections = self.content.sections
        moved = next((s for s in sections if s.key == p.section), None)
        if moved is None or p.after == p.section:
            return False
        if not any(s.key == p.after for s in sections):
            return False
        sections.remove(moved)
        sections.insert(next(n for n, s in enumerate(sections) if s.key == p.after), moved)
        return True
