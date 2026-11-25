"""Identifiers of the facts in a new version of the master profile (D118, D124). CV review
modifications cite these ids: an unchanged fact keeps its own, and a new fact receives a number
never taken by any past version (`taken`), even if the fact that carried it has gone.

- Archivist's draft: `merge_draft` takes the id of a fact of the last validated version with the
  same normalized text (role and company, degree and school, name, link, one-line text; an
  achievement or detail under the same parent), carries over January's facts (`sources`
  contains `january`: entered or confirmed in review) that the draft does not take, with their
  id, then numbers the rest; a fact of January rewritten in review no longer has the CV text:
  it replaces its counterpart in the draft, found on a loose key (company, school, name, label,
  first word of a skill), instead of being added next to it (D124);
- January's version: `keep_known` keeps the ids already assigned (a modified fact keeps its id),
  clears the others, then numbers the rest; a fact without a source comes from it (`january`)."""

from collections.abc import Callable, Collection, Iterable, Sequence
from typing import Any, Protocol, Self

from app.agents.tools.cv_schema import (
    FactSource,
    Identity,
    Language,
    Line,
    MasterProfileData,
    SkillFact,
    facts_of,
)
from app.agents.tools.cv_validator_facts import significant_words
from app.agents.tools.profile_check import plain
from app.features.cv.service.profile_numbering import HasId, children, number_new
from app.features.cv.service.profile_numbering import keep_known as keep_known  # noqa: PLC0414

_MAX_SOURCES = 4


class _Fact(Protocol):
    id: str
    sources: list[FactSource]


class _Copyable(_Fact, Protocol):
    def model_copy(self, *, deep: bool = False) -> Self: ...


def all_ids(profiles: Iterable[MasterProfileData]) -> set[str]:
    """All the ids assigned by these versions."""
    taken: set[str] = set()
    for profile in profiles:
        taken |= set(facts_of(profile))
    return taken


def _reuse[T: HasId](
    items: Sequence[T], before: Sequence[T], key: Callable[[T], str]
) -> list[tuple[T, T]]:
    """Sets on each element the id of the old element with the same key (each one used once),
    otherwise; returns the matched pairs."""
    pool: dict[str, list[T]] = {}
    for old in before:
        pool.setdefault(key(old), []).append(old)
    pairs: list[tuple[T, T]] = []
    for item in items:
        matches = pool.get(key(item))
        if matches:
            old = matches.pop(0)
            item.id = old.id
            pairs.append((item, old))
        else:
            item.id = ""
    return pairs


def _line_key(line: Line) -> str:
    return plain(line.text)


def _reuse_lines(pairs: Iterable[tuple[object, object]], field: str) -> None:
    """Achievements or details: ids carried over under the same matched parent."""
    for item, old in pairs:
        _reuse(getattr(item, field), getattr(old, field), _line_key)


def _clear_children(profile: MasterProfileData) -> None:
    for line in children(profile):
        line.id = ""


def _first_word(skill: SkillFact) -> str:
    return plain(skill.name).split(" ")[0]


def _text_in(small: str, big: str) -> bool:
    """All the significant words of `small` are in `big` ("Python" in "Python (expert)"), and
    there is at least one."""
    words = significant_words(small)
    return bool(words) and words <= significant_words(big)


def _carried[T: _Copyable](
    out: list[T],
    old: Sequence[T],
    pairs: Iterable[tuple[object, object]],
    loose: Callable[[T], str],
    text: Callable[[T], str],
    field: str | None = None,
    plain_fields: tuple[str, ...] = (),
) -> None:
    """January's facts from `old` that the draft did not take (no match). A fact for which the
    draft has only a counterpart (same loose key, unmatched, all its words in January's text:
    "Python" / "Python (expert)") replaces it, with the draft lines it does not have, its sources
    and those of its non-text fields (`plain_fields`: dates, place, URL) that it fills in (I-D:
    the new CV says where the experience ends); a field the draft does not state keeps January's
    value. Otherwise both are kept (a duplicate that January deletes is better than a fact of
    the new CV lost). The ids of `old` are kept."""
    used = {id(previous) for _, previous in pairs}
    for fact in old:
        if id(fact) in used or "january" not in fact.sources:
            continue
        kept, key = fact.model_copy(deep=True), loose(fact)
        twins = [
            i
            for i, item in enumerate(out)
            if key and not item.id and loose(item) == key and _text_in(text(item), text(fact))
        ]
        if len(twins) != 1:
            out.append(kept)
            continue
        draft = out[twins[0]]
        if field:
            lines: list[Line] = getattr(kept, field)
            have = {_line_key(line) for line in lines}
            lines.extend(x for x in getattr(draft, field) if _line_key(x) not in have)
        for name in plain_fields:
            if (value := getattr(draft, name)) is not None:
                setattr(kept, name, value)
        kept.sources = list(dict.fromkeys([*kept.sources, *draft.sources]))[:_MAX_SOURCES]
        out[twins[0]] = kept


def _carry_lines(pairs: Iterable[tuple[Any, Any]], field: str) -> None:
    """Under a matched parent of January, the lines of the old version absent from the draft (a
    fact confirmed in review is a line whose parent carries `january`); the draft's parent
    becomes so too. It also brings back a line that January had removed from their CV (the draft
    no longer carries it, the validated version still did: D124)."""
    for item, previous in pairs:
        if "january" not in previous.sources:
            continue
        lines = getattr(item, field)
        have = {_line_key(line) for line in lines}
        extra = [
            line.model_copy(deep=True)
            for line in getattr(previous, field)
            if _line_key(line) not in have
        ]
        lines.extend(extra)
        sources = item.sources
        if extra and "january" not in sources:
            sources.append("january")


def _keep_levels(pairs: Iterable[tuple[Language, Language]]) -> None:
    """A language matched by its name keeps January's level when the new CV does not state one;
    a level written by the CV wins (the level from before the confirmation is not kept)."""
    for language, previous in pairs:
        if "january" in previous.sources and language.level is None:
            language.level = previous.level
            language.sources = list(dict.fromkeys([*language.sources, "january"]))


def _carry_heads(out: MasterProfileData, old: MasterProfileData) -> None:
    """January's title and summary, if the draft has none."""
    for name in ("title", "summary"):
        previous: _Copyable | None = getattr(old, name)
        if getattr(out, name) is None and previous is not None and "january" in previous.sources:
            setattr(out, name, previous.model_copy(deep=True))


def _carry_facts(out: MasterProfileData, old: MasterProfileData, pairs: tuple[Any, ...]) -> None:
    """Carries over January's facts that the draft did not take, kind by kind (`_carried`);
    `pairs`: the matched pairs of `_reuse` in the order experiences, education, skills,
    projects, languages, links."""
    jobs, schools, skills, projects, languages, links = pairs
    name: Callable[[Any], str] = lambda x: x.name  # noqa: E731
    _carried(
        out.experiences,
        old.experiences,
        jobs,
        lambda x: plain(x.company),
        lambda x: x.role,
        "achievements",
        ("start", "end", "location"),
    )
    _carried(
        out.education,
        old.education,
        schools,
        lambda x: plain(x.school),
        lambda x: x.degree,
        "details",
        ("start", "end"),
    )
    _carried(out.skills, old.skills, skills, _first_word, name, None, ("category",))
    _carried(out.projects, old.projects, projects, lambda x: plain(x.name), name, "achievements")
    _carried(out.languages, old.languages, languages, lambda x: plain(x.name), name)
    _carried(
        out.links, old.links, links, lambda x: plain(x.label), lambda x: x.label, None, ("url",)
    )


def merge_draft(
    draft: MasterProfileData, previous: MasterProfileData | None, taken: Collection[str]
) -> MasterProfileData:
    """The numbered Archivist draft: ids of `previous` taken over, January's facts that the draft
    does not take carried over with their id, the other ids new."""
    out = draft.model_copy(deep=True)
    _clear_children(out)
    old = previous or MasterProfileData(identity=Identity(name="-"))
    _reuse([x for x in (out.title,) if x], [x for x in (old.title,) if x], _line_key)
    _reuse([x for x in (out.summary,) if x], [x for x in (old.summary,) if x], _line_key)
    jobs = _reuse(out.experiences, old.experiences, lambda x: plain(f"{x.role} {x.company}"))
    _reuse_lines(jobs, "achievements")
    schools = _reuse(out.education, old.education, lambda x: plain(f"{x.degree} {x.school}"))
    _reuse_lines(schools, "details")
    skills = _reuse(out.skills, old.skills, lambda x: plain(x.name))
    projects = _reuse(out.projects, old.projects, lambda x: plain(x.name))
    _reuse_lines(projects, "achievements")
    languages = _reuse(out.languages, old.languages, lambda x: plain(x.name))
    links = _reuse(out.links, old.links, lambda x: plain(x.url))
    _keep_levels(languages)
    _carry_lines(jobs, "achievements")
    _carry_lines(schools, "details")
    _carry_lines(projects, "achievements")
    _carry_heads(out, old)
    _carry_facts(out, old, (jobs, schools, skills, projects, languages, links))
    return number_new(out, taken)
