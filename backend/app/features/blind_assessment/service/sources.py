"""Lire deux CV détenus et retirer les identifiants avant la copie d’évaluation."""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.core.errors import AppError
from app.features.blind_assessment.schemas import BlindSourceOption
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.versions import (
    list_versions,
    validated_profile,
    version_content,
    version_numbers,
    version_ref,
)

_HIDDEN = "[masqué]"
_EMAIL = re.compile(r"(?<!\w)[\w.+%-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+\d{1,3}[ .()-]*|0)(?:\d[ .()-]*){8,12}\d(?!\w)")
_MAX_CHARACTERS = 24_000


@dataclass(frozen=True)
class BlindVersion:
    id: str
    label: str
    text: str


async def choices(rt: CvRuntime, user_id: str) -> list[BlindSourceOption]:
    return [
        BlindSourceOption(
            id=row.id,
            label=f"CV n°{row.number} · {row.filename}",
            created_at=row.created_at,
        )
        for row in await list_versions(rt, user_id, None)
        if row.status == "ready"
    ]


def _parts(cv: CvContent) -> Iterable[str]:
    if cv.headline:
        yield cv.headline
    for section in cv.sections:
        if section.key == "links":
            continue
        yield section.title
        for entry in section.entries:
            yield " · ".join(
                value for value in (entry.heading, entry.subheading, entry.dates) if value
            )
            yield from (line.text for line in entry.lines)
        yield from (line.text for line in section.items)


def _name_variants(name: str) -> set[str]:
    plain = "".join(
        char for char in unicodedata.normalize("NFKD", name) if not unicodedata.combining(char)
    )
    return {name, plain, *re.findall(r"[^\W\d_]{3,}", f"{name} {plain}")}


def _redactions(
    pair: tuple[CvContent, CvContent], profile: MasterProfileData | None
) -> re.Pattern[str]:
    terms: set[str] = set()
    for source in pair:
        terms.update(_name_variants(source.name))
        terms.update(source.contact)
    if profile is not None:
        identity = profile.identity
        terms.update(_name_variants(identity.name))
        terms.update(
            value for value in (identity.email, identity.phone, identity.location) if value
        )
        terms.update(link.url for link in profile.links)
    ordered = sorted(
        {unicodedata.normalize("NFKC", value.strip()) for value in terms if value.strip()},
        key=len,
        reverse=True,
    )
    if not ordered:
        return re.compile(r"(?!)")
    alternatives = "|".join(re.escape(value) for value in ordered)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def anonymized(cv: CvContent, redactions: re.Pattern[str]) -> str:
    scrubbed = redactions.sub(_HIDDEN, unicodedata.normalize("NFKC", "\n".join(_parts(cv))))
    for generic in (_EMAIL, _URL, _PHONE):
        scrubbed = generic.sub(_HIDDEN, scrubbed)
    value = scrubbed.strip()
    if not value or len(value) > _MAX_CHARACTERS:
        raise AppError(
            "blind_source_length", "Le texte anonymisé est vide ou trop long pour la grille.", 422
        )
    return value


async def _ready(db: AsyncSession, user_id: str, version_id: str) -> CvContent:
    ref = await version_ref(db, user_id, version_id)
    if ref is None or ref[1] != "ready":
        raise AppError("blind_source_not_found", "Version de CV prête introuvable.", 404)
    content = await version_content(db, user_id, version_id)
    if content is None:
        raise AppError("blind_source_unreadable", "Cette version de CV est illisible.", 409)
    return content


async def source_pair(
    db: AsyncSession, user_id: str, first: str, second: str
) -> tuple[BlindVersion, BlindVersion]:
    left = await _ready(db, user_id, first)
    right = await _ready(db, user_id, second)
    numbers = await version_numbers(db, user_id, [first, second])
    if first not in numbers or second not in numbers:
        raise AppError("blind_source_not_found", "Version de CV prête introuvable.", 404)
    redactions = _redactions((left, right), await validated_profile(db, user_id))
    a = BlindVersion(first, f"CV n°{numbers[first]}", anonymized(left, redactions))
    b = BlindVersion(second, f"CV n°{numbers[second]}", anonymized(right, redactions))
    if a.text == b.text:
        raise AppError(
            "blind_sources_identical", "Ces versions ont le même texte après anonymisation.", 409
        )
    return a, b
