"""Un fait confirmé par January entre au profil maître (SPEC 1, 5.5 ; D130 n° 3) : quand elle
confirme une modification « à confirmer » (chiffre, outil, titre absent du profil), le fait visé
par la modification est réécrit avec son texte dans une **nouvelle version validée** (source
`january`, ids gardés, compétences déclarées : `save_profile`). Jamais journalisé."""

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.agents.tools.cv_schema import FactSource, MasterProfileData
from app.core.errors import AppError
from app.features.cv.repository import ProfileRepository
from app.features.cv.schemas_profile import ProfilePutIn
from app.features.cv.service.profile import save_profile
from app.features.cv.service.runtime import CvRuntime

SEP = " — "  # séparateur des faits composés (« Rôle — Entreprise », `facts_of`)
_MAX_SOURCES = 4
# Séparateur rôle / entreprise, libellé / URL (D137) : « — », ou « – » et « - » entourés
# d'espaces (un trait d'union collé aux mots n'en est jamais un) ; aussi quand la fin a été rognée.
_EM_SEP = re.compile(r"\s+—(?:\s+|$)")
_SEP = re.compile(r"\s+[—–-](?:\s+|$)")
_LANG_SEP = re.compile(r"\s+[—–-](?:\s+|$)|\s*:\s*")  # « Anglais — C1 », « - C1 », « : C1 »
_LANG_PAREN = re.compile(r"^(.+?)\s*\((.+)\)$")  # « Anglais (C1) »
_URL_LIKE = re.compile(r"://|\b[\w-]+(?:\.[\w-]+)+/|www\.", re.IGNORECASE)


def fact_not_found() -> AppError:
    return AppError(
        "fact_not_found",
        "Le fait visé n'est plus dans ton profil maître : modifie ton profil puis relance "
        "une revue.",
        409,
    )


def profile_draft_pending() -> AppError:
    return AppError(
        "profile_draft_pending",
        "Un brouillon de ton profil attend ta validation : valide-le avant de confirmer ce fait.",
        409,
    )


def invalid_after() -> AppError:
    return AppError(
        "validation_error",
        "Requête invalide : vérifie les champs signalés.",
        422,
        {"fields": ["after"]},
    )


def _valid_url(url: str) -> bool:
    """Une URL http(s) avec un hôte, sans espace (jamais de `javascript:` dans le profil)."""
    try:
        parts = urlsplit(url)
    except ValueError:  # « http://[::1 »
        return False
    return (
        parts.scheme in ("http", "https")
        and bool(parts.hostname)
        and not re.search(r"\s|[<>\"]", url)
    )


def _write_language(item: Any, text: str) -> None:
    """« Nom — niveau » (aussi « - », « : » et « Nom (niveau) ») écrit le nom et le niveau ; la
    parenthèse passe avant le deux-points quand le nom, devant elle, n'a pas de séparateur
    (« Anglais (TOEIC: 950) ») ; sans séparateur le texte entier est le nom et le niveau est
    effacé : jamais l'ancien niveau à côté d'un texte neuf."""
    paren = _LANG_PAREN.match(text)
    if paren and not _LANG_SEP.search(paren.group(1)):
        parts = [paren.group(1), paren.group(2)]
    else:
        parts = _LANG_SEP.split(text, maxsplit=1)
    item.name = parts[0].strip()
    item.level = parts[1].strip() or None if len(parts) > 1 else None


def _split_last(text: str) -> tuple[str, str] | None:
    """Coupe `text` au dernier séparateur : le dernier « — » s'il y en a un, sinon le dernier
    « – » ou « - » entouré d'espaces ; `None` sans séparateur (D137)."""
    for pattern in (_EM_SEP, _SEP):
        if found := list(pattern.finditer(text)):
            return text[: found[-1].start()], text[found[-1].end() :]
    return None


def _split_company(text: str, current: str) -> tuple[str, str]:
    """« Rôle — Entreprise » → (rôle, entreprise) ; le texte qui finit par l'entreprise connue la
    garde, un texte sans séparateur ne change que le rôle (l'entreprise reste, D137)."""
    suffix = f"{SEP}{current}"
    if text.endswith(suffix):
        return text[: -len(suffix)].strip(), current
    cut = _split_last(text)
    return cut if cut else (text, current)


def _write_link(item: Any, text: str) -> None:
    """« Libellé — URL » écrit le libellé et l'URL (http ou https, sinon 422) ; une URL seule
    remplace l'URL ; un texte sans URL ne change que le libellé."""
    cut = _split_last(text)
    label, url = cut if cut else ("", text)
    if label:
        item.label, item.url = label, url
    elif _URL_LIKE.search(text):
        item.url = text
    else:
        item.label = text
    if (label or _URL_LIKE.search(text)) and not _valid_url(item.url):
        raise invalid_after()


def _sourced(item: Any) -> None:
    sources: list[FactSource] = item.sources
    if "january" not in sources and len(sources) < _MAX_SOURCES:
        sources.append("january")


def _write_lines(lines: list[Any], target: str, text: str) -> bool:
    for line in lines:
        if line.id == target:
            line.text = text
            return True
    return False


def _entries(data: MasterProfileData, target: str, text: str) -> bool:
    """Expériences, formations, projets : l'intitulé ou une de leurs lignes."""
    for x in data.experiences:
        if x.id == target:
            x.role, x.company = _split_company(text, x.company)
        if x.id == target or _write_lines(x.achievements, target, text):
            _sourced(x)
            return True
    for e in data.education:
        if e.id == target:
            e.degree, e.school = _split_company(text, e.school)
        if e.id == target or _write_lines(e.details, target, text):
            _sourced(e)
            return True
    for p in data.projects:
        if p.id == target:
            p.name = text
        if p.id == target or _write_lines(p.achievements, target, text):
            _sourced(p)
            return True
    return False


def _flat(data: MasterProfileData, target: str, text: str) -> bool:
    """Titre, résumé, compétences, langues, liens."""
    heads = [line for line in (data.title, data.summary) if line is not None]
    writers: list[tuple[list[Any], Callable[[Any], None]]] = [
        (heads, lambda item: setattr(item, "text", text)),
        (data.skills, lambda item: setattr(item, "name", text)),
        (data.languages, lambda item: _write_language(item, text)),
        (data.links, lambda item: _write_link(item, text)),
    ]
    for items, write in writers:
        for item in items:
            if item.id == target:
                write(item)
                _sourced(item)
                return True
    return False


def with_fact(profile: MasterProfileData, target: str, text: str) -> MasterProfileData:
    """Le profil où le fait `target` dit `text` ; 409 `fact_not_found`, 422 si le texte ne
    tient pas dans le champ du fait."""
    data = profile.model_copy(deep=True)
    if not (_flat(data, target, text) or _entries(data, target, text)):
        raise fact_not_found()
    try:
        return MasterProfileData.model_validate(data.model_dump())
    except ValidationError:
        raise invalid_after() from None


async def confirm_fact(rt: CvRuntime, user_id: str, target: str | None, text: str) -> int:
    """Nouvelle version validée du profil avec le fait confirmé ; rend son numéro. 409
    `profile_draft_pending` quand un brouillon plus récent que la version validée attend January :
    la nouvelle version passerait au-dessus de lui et l'enterrerait (revue 6.14, I-1)."""
    async with rt.session_factory() as db:
        repo = ProfileRepository(db, user_id)
        latest = await repo.latest("validated")
        top = await repo.top_version()
    if latest is None or not target:
        raise fact_not_found()
    if top > latest.version:  # une version plus récente que la validée est un brouillon
        raise profile_draft_pending()
    data = with_fact(MasterProfileData.model_validate(latest.data), target, text)
    saved = await save_profile(rt, user_id, ProfilePutIn(data=data, base_version=top or None))
    return saved.version
