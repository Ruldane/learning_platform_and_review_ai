"""L'honnêteté commence au profil (SPEC 5.1, 18.3 ; D124) : contrôles par le code du brouillon de
l'Archiviste, sans appel au modèle.

- `unsupported_lines` : une réalisation ou un détail dont un nombre n'apparaît dans aucune source
  est retiré (formats canonisés par `cv_lexicon.numbers_in`) ;
- `tag_sources` : les `sources` d'un fait sont posées par le code, d'après les documents où son
  texte principal apparaît ; un fait introuvable vient de la note si January en a écrit une,
  sinon il est retiré.

Le titre et le résumé (`SourcedLine`) sont des faits comme les autres : sans eux, un résumé tiré
de LinkedIn seul entrerait dans le CV ciblé (`in_cv`)."""

import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from app.agents.tools.cv_lexicon import numbers_in
from app.agents.tools.cv_schema import FactSource, Line, MasterProfileData, facts_of
from app.agents.tools.profile_port import ProfileSource

_NOT_WORD = re.compile(r"[^\w+#]+")
_CHILD = re.compile(r"^([a-z]\d+)[ad]\d+$")
_SCHEME = re.compile(r"^\s*(https?://)?(www\.)?", re.IGNORECASE)
# Un texte long (résumé) reformulé ligne à ligne : 80 % de ses mots de 3 lettres et plus suffisent.
_LONG_WORDS = 6
_LONG_SHARE = 0.8


class _Fact(Protocol):
    id: str
    sources: list[FactSource]


def plain(text: str) -> str:
    """Sans accents, en minuscules, ponctuation réduite à des espaces (« C++ », « C# » restent)."""
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _NOT_WORD.sub(" ", bare.casefold()).strip()


def appears(needle: str, haystack: str) -> bool:
    """`needle` figure dans `haystack` (déjà passé par `plain`), en mots entiers ; un texte d'au
    moins `_LONG_WORDS` mots y figure si `_LONG_SHARE` de ses mots y sont."""
    wanted = plain(needle)
    if not wanted:
        return False
    if f" {wanted} " in f" {haystack} ":
        return True
    words = [word for word in wanted.split() if len(word) >= 3]
    if len(words) < _LONG_WORDS:
        return False
    present = set(haystack.split())
    return sum(word in present for word in words) >= _LONG_SHARE * len(words)


def blank_facts(profile: MasterProfileData) -> MasterProfileData:
    """Une copie sans les ids ni les sources rendus par le modèle : le code les pose."""
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
    """Les réalisations et détails, dans l'ordre du profil."""
    for experience in profile.experiences:
        yield from experience.achievements
    for education in profile.education:
        yield from education.details
    for project in profile.projects:
        yield from project.achievements


def unsupported_lines(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> list[str]:
    """Ids des réalisations et détails dont un nombre n'apparaît dans aucune source."""
    known: set[str] = set()
    for source in sources:
        known |= numbers_in(source.text)
    return [line.id for line in _lines(profile) if numbers_in(line.text) - known]


def without_lines(profile: MasterProfileData, ids: Iterable[str]) -> MasterProfileData:
    """Une copie sans les réalisations et détails `ids`."""
    gone = set(ids)
    out = profile.model_copy(deep=True)
    for experience in out.experiences:
        experience.achievements = [x for x in experience.achievements if x.id not in gone]
    for education in out.education:
        education.details = [x for x in education.details if x.id not in gone]
    for project in out.projects:
        project.achievements = [x for x in project.achievements if x.id not in gone]
    return out


def _found_in(texts: Sequence[str], sources: Sequence[tuple[FactSource, str]]) -> list[FactSource]:
    """Les sources (hors note) où chacun des `texts` apparaît."""
    return [kind for kind, hay in sources if all(appears(text, hay) for text in texts)]


def _tagged[T: _Fact](
    facts: Sequence[T],
    main: Callable[[T], Sequence[str]],
    sources: Sequence[tuple[FactSource, str]],
    has_note: bool,
) -> list[T]:
    kept: list[T] = []
    for fact in facts:
        found = _found_in(main(fact), sources)
        if not found and has_note:
            found = ["note"]
        if found:
            fact.sources = found
            kept.append(fact)
    return kept


def tag_sources(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> MasterProfileData:
    """Une copie où les `sources` de chaque fait sont celles des documents où son texte principal
    apparaît (titre, résumé, rôle et entreprise, diplôme et école, nom, lien sans `https://` ni
    `www.`) ; aucune → `note`
    si la note existe, sinon le fait est retiré (avec ses réalisations)."""
    docs: list[tuple[FactSource, str]] = [
        (s.kind, plain(s.text)) for s in sources if s.kind != "note"
    ]
    note = any(s.kind == "note" and s.text.strip() for s in sources)
    out = profile.model_copy(deep=True)
    out.title = next(iter(_tagged([out.title] if out.title else [], _text, docs, note)), None)
    out.summary = next(iter(_tagged([out.summary] if out.summary else [], _text, docs, note)), None)
    out.experiences = _tagged(out.experiences, lambda x: (x.role, x.company), docs, note)
    out.education = _tagged(out.education, lambda x: (x.degree, x.school), docs, note)
    out.skills = _tagged(out.skills, lambda x: (x.name,), docs, note)
    out.projects = _tagged(out.projects, lambda x: (x.name,), docs, note)
    out.languages = _tagged(out.languages, lambda x: (x.name,), docs, note)
    out.links = _tagged(out.links, lambda x: (_SCHEME.sub("", x.url),), docs, note)
    return out


def _text(line: Line) -> Sequence[str]:
    return (line.text,)


def removed_facts(before: MasterProfileData, after: MasterProfileData) -> list[str]:
    """Texte lisible des faits de `before` absents de `after` (ids posés), sans les réalisations
    et détails d'un parent retiré avec lui."""
    old, new = facts_of(before), facts_of(after)
    gone = [fact_id for fact_id in old if fact_id not in new]
    parents = set(gone)
    return [
        old[fact_id]
        for fact_id in gone
        if not ((match := _CHILD.match(fact_id)) and match.group(1) in parents)
    ]
