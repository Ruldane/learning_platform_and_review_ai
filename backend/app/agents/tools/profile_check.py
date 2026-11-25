"""Honesty starts with the profile (SPEC 5.1, 18.3; D124): code checks of the Archivist's draft,
with no model call.

- `unsupported_lines`: an achievement, a detail, the title, the summary or the description of a
  project whose number appears in no source is removed (formats canonicalized by
  `cv_lexicon.numbers_in`) ;
- `untraced_lines`: an achievement or detail without a number that the documents say neither word
  for word nor at 80% of its words (rule of `appears`) is removed likewise (final review 6.8 M3);
- `tag_sources`: a fact's `sources` are set by the code, from the documents where its
  main text appears; a fact not found in the documents comes from the note only if
  the note carries it (same rule), otherwise it is removed.

A reworded text (80% rule) must keep all its numbers and all its names (acronyms, proper
nouns, tools: `named_terms`): "15 years" against "five years", or an added "Kubernetes",
do not pass.

The title and summary (`SourcedLine`) are facts like the others: without them, a summary taken
from LinkedIn alone would enter the targeted CV (`in_cv`)."""

import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.agents.tools.cv_lexicon import numbers_in
from app.agents.tools.cv_schema import FactSource, Line, MasterProfileData, Project, facts_of
from app.agents.tools.profile_port import ProfileSource

_NOT_WORD = re.compile(r"[^\w+#]+")
_CHILD = re.compile(r"^([a-z]\d+)[ad]\d+$")
_SCHEME = re.compile(r"^\s*(https?://)?(www\.)?", re.IGNORECASE)
_TOKEN = re.compile(r"[\w+#]+")
_SENTENCE_BREAK = re.compile(r"[.!?:;\u2022\n]")
# A long text (summary) reworded line by line: 80% of its words of 3 letters or more are enough.
_SHORT_NAME = 2  # "C", "Go": searched with their case (`_short_name_in`)
_LONG_WORDS = 6
_LONG_SHARE = 0.8


class _Fact(Protocol):
    id: str
    sources: list[FactSource]


def plain(text: str) -> str:
    """Without accents, in lower case, punctuation reduced to spaces ("C++", "C#" stay)."""
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _NOT_WORD.sub(" ", bare.casefold()).strip()


@dataclass(frozen=True)
class Hay:
    """A source ready to search: `plain` text, its words, its canonical numbers."""

    kind: FactSource
    text: str
    words: frozenset[str]
    numbers: frozenset[str]
    raw: str = ""  # the text as written: a one- or two-letter name is searched with its case

    @classmethod
    def of(cls, source: ProfileSource) -> "Hay":
        text = plain(source.text)
        words, numbers = frozenset(text.split()), frozenset(numbers_in(source.text))
        return cls(source.kind, text, words, numbers, source.text)


def named_terms(text: str) -> set[str]:
    """The words that carry a fact without being numbers (`plain`): acronyms ("IA"), words with
    a digit ("S3"), proper nouns and tools (capital letter not at the start of a sentence)."""
    found: set[str] = set()
    start, end = True, 0
    for match in _TOKEN.finditer(text):
        token = match.group()
        start = start or bool(_SENTENCE_BREAK.search(text, end, match.start()))
        end = match.end()
        if any(ch.isalpha() for ch in token) and (
            any(ch.isdigit() for ch in token)
            or any(ch.isupper() for ch in token[1:])
            or (token[0].isupper() and not start)
        ):
            found.add(plain(token))
        start = False
    return found


def _short_name_in(needle: str, raw: str) -> bool:
    """A name of one or two letters ("C", "Go", "R") is written as is in the text: neither
    elision ("C'est"), nor unit ("10 Go"), nor followed by another name.
    ("C++", "C#", "R&D", "C-level")."""
    pattern = rf"(?<![\w'’.\-])(?<!\d )(?<!\d\u00a0){re.escape(needle.strip())}(?![\w'’+#&\-])"
    return re.search(pattern, raw) is not None


def appears(needle: str, hay: Hay) -> bool:
    """`needle` appears in `hay`, as whole words and with all its numbers; a text of at least
    `_LONG_WORDS` words appears there if `_LONG_SHARE` of its words do, and all its names too."""
    wanted = plain(needle)
    if not wanted or not numbers_in(needle) <= hay.numbers:
        return False
    if len(wanted) <= _SHORT_NAME and wanted.isalpha():
        return _short_name_in(needle, hay.raw)
    if f" {wanted} " in f" {hay.text} ":
        return True
    words = [word for word in wanted.split() if len(word) >= 3]
    if len(words) < _LONG_WORDS or not named_terms(needle) <= hay.words:
        return False
    return sum(word in hay.words for word in words) >= _LONG_SHARE * len(words)


def blank_facts(profile: MasterProfileData) -> MasterProfileData:
    """A copy without the ids and sources returned by the model: the code sets them."""
    out = profile.model_copy(deep=True)
    heads = [line for line in (out.title, out.summary) if line is not None]
    facts: list[_Fact] = [
        *heads,
        *out.experiences,
        *out.education,
        *out.skills,
        *out.projects,
        *out.languages,
        *out.links,
    ]
    for fact in facts:
        fact.id, fact.sources = "", []
    for child in _lines(out):
        child.id = ""
    return out


def _lines(profile: MasterProfileData) -> Iterable[Line]:
    """The achievements and details, in profile order."""
    for experience in profile.experiences:
        yield from experience.achievements
    for education in profile.education:
        yield from education.details
    for project in profile.projects:
        yield from project.achievements


def unsupported_lines(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> list[str]:
    """Ids of the lines whose number appears in no source: title, summary, achievements
    and details, and the id of a project whose description carries such a number."""
    known: set[str] = set()
    for source in sources:
        known |= numbers_in(source.text)
    heads = [line for line in (profile.title, profile.summary) if line is not None]
    lines = [line.id for line in [*heads, *_lines(profile)] if numbers_in(line.text) - known]
    described = [p.id for p in profile.projects if numbers_in(p.description) - known]
    return lines + described


def untraced_lines(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> list[str]:
    """Ids of the achievements and details without a number that no source carries (`appears`,
    note included): "Migrated production to Kubernetes" invented under a real experience."""
    hays = [Hay.of(source) for source in sources if source.text.strip()]
    return [
        line.id
        for line in _lines(profile)
        if not numbers_in(line.text) and not any(appears(line.text, hay) for hay in hays)
    ]


def without_lines(profile: MasterProfileData, ids: Iterable[str]) -> MasterProfileData:
    """A copy without the `ids` lines; a project's id only removes its description."""
    gone = set(ids)
    out = profile.model_copy(deep=True)
    if out.title is not None and out.title.id in gone:
        out.title = None
    if out.summary is not None and out.summary.id in gone:
        out.summary = None
    for experience in out.experiences:
        experience.achievements = [x for x in experience.achievements if x.id not in gone]
    for education in out.education:
        education.details = [x for x in education.details if x.id not in gone]
    for project in out.projects:
        project.achievements = [x for x in project.achievements if x.id not in gone]
        if project.id in gone:
            project.description = ""
    return out


def _found_in(texts: Sequence[str], hays: Sequence[Hay]) -> list[FactSource]:
    """The sources where each of the `texts` appears."""
    return [hay.kind for hay in hays if all(appears(text, hay) for text in texts)]


def _tagged[T: _Fact](
    facts: Sequence[T],
    main: Callable[[T], Sequence[str]],
    docs: Sequence[Hay],
    notes: Sequence[Hay],
) -> list[T]:
    kept: list[T] = []
    for fact in facts:
        found = _found_in(main(fact), docs) or _found_in(main(fact), notes)
        if found:
            fact.sources = found
            kept.append(fact)
    return kept


def tag_sources(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> MasterProfileData:
    """A copy where each fact's `sources` are those of the documents where its main text
    appears (title, summary, role and company, degree and school, project name and description
    names, link without `https://` or `www.`); none -> `note` if the note carries it (same
    rule), otherwise the fact is removed (with its achievements)."""
    hays = [Hay.of(s) for s in sources if s.text.strip()]
    docs = [hay for hay in hays if hay.kind != "note"]
    note = [hay for hay in hays if hay.kind == "note"]
    out = profile.model_copy(deep=True)
    out.title = next(iter(_tagged([out.title] if out.title else [], _text, docs, note)), None)
    out.summary = next(iter(_tagged([out.summary] if out.summary else [], _text, docs, note)), None)
    out.experiences = _tagged(out.experiences, lambda x: (x.role, x.company), docs, note)
    out.education = _tagged(out.education, lambda x: (x.degree, x.school), docs, note)
    out.skills = _tagged(out.skills, lambda x: (x.name,), docs, note)
    out.projects = _tagged(out.projects, _project, docs, note)
    out.languages = _tagged(out.languages, lambda x: (x.name,), docs, note)
    out.links = _tagged(out.links, lambda x: (_SCHEME.sub("", x.url),), docs, note)
    return out


def _text(line: Line) -> Sequence[str]:
    return (line.text,)


def _project(project: Project) -> Sequence[str]:
    """The name, and each proper noun, acronym or tool of the description: an invented tool in the
    description does not slip under a real project."""
    return (project.name, *sorted(named_terms(project.description)))


def removed_facts(before: MasterProfileData, after: MasterProfileData) -> list[str]:
    """Readable text of the facts of `before` absent from `after` (ids set), minus the
    achievements and details of a parent removed with it."""
    old, new = facts_of(before), facts_of(after)
    gone = [fact_id for fact_id in old if fact_id not in new]
    parents = set(gone)
    return [
        old[fact_id]
        for fact_id in gone
        if not ((match := _CHILD.match(fact_id)) and match.group(1) in parents)
    ]
