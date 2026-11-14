"""L'honnêteté commence au profil (SPEC 5.1, 18.3 ; D124) : contrôles par le code du brouillon de
l'Archiviste, sans appel au modèle.

- `unsupported_lines` : une réalisation, un détail, le titre, le résumé ou la description d'un
  projet dont un nombre n'apparaît dans aucune source est retiré (formats canonisés par
  `cv_lexicon.numbers_in`) ;
- `untraced_lines` : une réalisation ou un détail sans nombre que les documents ne disent ni mot
  pour mot ni à 80 % de ses mots (règle de `appears`) est retiré de même (revue finale 6.8 M3) ;
- `tag_sources` : les `sources` d'un fait sont posées par le code, d'après les documents où son
  texte principal apparaît ; un fait introuvable dans les documents vient de la note seulement si
  la note le porte (même règle), sinon il est retiré.

Un texte reformulé (règle des 80 %) doit garder tous ses nombres et tous ses noms (sigles, noms
propres, outils : `named_terms`) : « 15 ans » face à « cinq ans », ou un « Kubernetes » ajouté,
ne passent pas.

Le titre et le résumé (`SourcedLine`) sont des faits comme les autres : sans eux, un résumé tiré
de LinkedIn seul entrerait dans le CV ciblé (`in_cv`)."""

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
# Un texte long (résumé) reformulé ligne à ligne : 80 % de ses mots de 3 lettres et plus suffisent.
_SHORT_NAME = 2  # « C », « Go » : cherchés avec leur casse (`_short_name_in`)
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


@dataclass(frozen=True)
class Hay:
    """Une source prête à chercher : texte `plain`, ses mots, ses nombres canoniques."""

    kind: FactSource
    text: str
    words: frozenset[str]
    numbers: frozenset[str]
    raw: str = ""  # le texte tel qu'écrit : un nom d'une ou deux lettres s'y cherche avec sa casse

    @classmethod
    def of(cls, source: ProfileSource) -> "Hay":
        text = plain(source.text)
        words, numbers = frozenset(text.split()), frozenset(numbers_in(source.text))
        return cls(source.kind, text, words, numbers, source.text)


def named_terms(text: str) -> set[str]:
    """Les mots qui portent un fait sans être des nombres (`plain`) : sigles (« IA »), mots à
    chiffre (« S3 »), noms propres et outils (majuscule hors début de phrase)."""
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
    """Un nom d'une ou deux lettres (« C », « Go », « R ») s'écrit tel quel dans le texte : ni
    élision (« C'est »), ni unité (« 10 Go »), ni suite d'un autre nom
    (« C++ », « C# », « R&D », « C-level »)."""
    pattern = rf"(?<![\w'’.\-])(?<!\d )(?<!\d\u00a0){re.escape(needle.strip())}(?![\w'’+#&\-])"
    return re.search(pattern, raw) is not None


def appears(needle: str, hay: Hay) -> bool:
    """`needle` figure dans `hay`, en mots entiers et avec tous ses nombres ; un texte d'au moins
    `_LONG_WORDS` mots y figure si `_LONG_SHARE` de ses mots y sont, et tous ses noms aussi."""
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
    """Ids des lignes dont un nombre n'apparaît dans aucune source : titre, résumé, réalisations
    et détails, et l'id d'un projet dont la description porte un tel nombre."""
    known: set[str] = set()
    for source in sources:
        known |= numbers_in(source.text)
    heads = [line for line in (profile.title, profile.summary) if line is not None]
    lines = [line.id for line in [*heads, *_lines(profile)] if numbers_in(line.text) - known]
    described = [p.id for p in profile.projects if numbers_in(p.description) - known]
    return lines + described


def untraced_lines(profile: MasterProfileData, sources: Sequence[ProfileSource]) -> list[str]:
    """Ids des réalisations et détails sans nombre qu'aucune source ne porte (`appears`, note
    comprise) : « Migré la production vers Kubernetes » inventé sous une vraie expérience."""
    hays = [Hay.of(source) for source in sources if source.text.strip()]
    return [
        line.id
        for line in _lines(profile)
        if not numbers_in(line.text) and not any(appears(line.text, hay) for hay in hays)
    ]


def without_lines(profile: MasterProfileData, ids: Iterable[str]) -> MasterProfileData:
    """Une copie sans les lignes `ids` ; l'id d'un projet n'efface que sa description."""
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
    """Les sources où chacun des `texts` apparaît."""
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
    """Une copie où les `sources` de chaque fait sont celles des documents où son texte principal
    apparaît (titre, résumé, rôle et entreprise, diplôme et école, nom et noms de la description
    d'un projet, lien sans `https://` ni `www.`) ; aucune → `note` si la note le porte (même
    règle), sinon le fait est retiré (avec ses réalisations)."""
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
    """Le nom, et chaque nom propre, sigle ou outil de la description : un outil inventé dans la
    description ne se glisse pas sous un vrai projet."""
    return (project.name, *sorted(named_terms(project.description)))


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
