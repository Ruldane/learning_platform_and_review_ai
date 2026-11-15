"""Identifiants des faits d'une nouvelle version du profil maître (D118, D124). Les modifications
des revues de CV citent ces ids : un fait inchangé garde le sien, un fait neuf reçoit un numéro
jamais pris par aucune version passée (`taken`), même si le fait qui le portait a disparu.

- brouillon de l'Archiviste : `merge_draft` reprend l'id d'un fait de la dernière version validée
  au même texte normalisé (rôle et entreprise, diplôme et école, nom, lien, texte d'une ligne ; une
  réalisation ou un détail sous le même parent), reporte les faits de January (`sources` contient
  `january` : saisis ou confirmés en revue) que le brouillon ne reprend pas, avec leur id, puis
  numérote le reste ; un fait de January réécrit en revue n'a plus le texte du CV : il remplace
  son équivalent du brouillon, trouvé à une clé lâche (entreprise, école, nom, libellé, premier
  mot d'une compétence), au lieu de s'y ajouter (D124) ;
- version de January : `keep_known` garde les ids déjà attribués (un fait modifié garde son id),
  efface les autres, puis numérote le reste ; un fait sans source vient d'elle (`january`)."""

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
    """Tous les ids attribués par ces versions."""
    taken: set[str] = set()
    for profile in profiles:
        taken |= set(facts_of(profile))
    return taken


def _reuse[T: HasId](
    items: Sequence[T], before: Sequence[T], key: Callable[[T], str]
) -> list[tuple[T, T]]:
    """Pose sur chaque élément l'id de l'ancien élément de même clé (chacun servi une fois), ""
    sinon ; rend les paires appariées."""
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
    """Réalisations ou détails : ids repris sous un même parent apparié."""
    for item, old in pairs:
        _reuse(getattr(item, field), getattr(old, field), _line_key)


def _clear_children(profile: MasterProfileData) -> None:
    for line in children(profile):
        line.id = ""


def _first_word(skill: SkillFact) -> str:
    return plain(skill.name).split(" ")[0]


def _text_in(small: str, big: str) -> bool:
    """Tous les mots significatifs de `small` sont dans `big` (« Python » dans « Python (expert) »),
    et il y en a au moins un."""
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
    """Les faits de January de `old` que le brouillon n'a pas repris (aucun apparié). Un fait dont
    le brouillon n'a qu'un équivalent (même clé lâche, non apparié, tous ses mots dans le texte de
    January : « Python » / « Python (expert) ») le remplace, avec les lignes du brouillon qu'il n'a
    pas, ses sources et ceux de ses champs non textuels (`plain_fields` : dates, lieu, URL) qu'il
    renseigne (I-D : le nouveau CV dit où l'expérience finit) ; un champ que le brouillon ne dit
    pas garde la valeur de January. Sinon les deux sont gardés (un doublon que January efface vaut
    mieux qu'un fait du nouveau CV perdu). Les ids de `old` sont gardés."""
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
    """Sous un parent apparié de January, les lignes de l'ancienne version absentes du brouillon
    (un fait confirmé en revue est une ligne dont le parent porte `january`) ; le parent du
    brouillon le devient aussi. Elle ramène aussi une ligne que January avait retirée de son CV
    (le brouillon ne la porte plus, la version validée la portait encore : D124)."""
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
    """Une langue appariée par son nom garde le niveau de January quand le nouveau CV n'en dit pas ;
    un niveau écrit par le CV l'emporte (le niveau d'avant la confirmation n'est pas conservé)."""
    for language, previous in pairs:
        if "january" in previous.sources and language.level is None:
            language.level = previous.level
            language.sources = list(dict.fromkeys([*language.sources, "january"]))


def _carry_heads(out: MasterProfileData, old: MasterProfileData) -> None:
    """Le titre et le résumé de January, si le brouillon n'en a pas."""
    for name in ("title", "summary"):
        previous: _Copyable | None = getattr(old, name)
        if getattr(out, name) is None and previous is not None and "january" in previous.sources:
            setattr(out, name, previous.model_copy(deep=True))


def _carry_facts(out: MasterProfileData, old: MasterProfileData, pairs: tuple[Any, ...]) -> None:
    """Reporte les faits de January que le brouillon n'a pas repris, sorte par sorte (`_carried`) ;
    `pairs` : les paires appariées de `_reuse` dans l'ordre expériences, formations, compétences,
    projets, langues, liens."""
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
    """Le brouillon de l'Archiviste numéroté : ids de `previous` repris, les faits de January que
    le brouillon ne reprend pas reportés avec leur id, les autres ids neufs."""
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
