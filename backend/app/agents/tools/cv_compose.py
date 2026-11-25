"""Composition of the targeted CV by the code (SPEC 5.3, criterion 18.3): the model never writes
the CV. The content starts from the facts of the original CV (`base_content`), then receives the
accepted changes (`apply_modifications`). Each line carries the identifiers of the profile facts
it comes from: no line without a fact.

The module does not judge: the check against the profile (`cv_validator`) and the user's
decision come before. It only refuses to write what it cannot place: a target absent from the
content or the profile is ignored, counted, and returned to the caller."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.agents.tools.cv_compose_ops import SECTION_TITLES, Composer, heads
from app.agents.tools.cv_schema import (
    CvContent,
    CvEntry,
    CvLine,
    CvSection,
    MasterProfileData,
    SectionKey,
    facts_of,
    in_cv,
)
from app.agents.tools.review_schema import Proposal

logger = logging.getLogger(__name__)

_ACTION_ORDER = {"remove": 0, "rewrite": 1, "add": 2, "move": 3}


@dataclass(frozen=True)
class Applied:
    """The composed content and the references of the ignored changes (target not found)."""

    content: CvContent
    ignored: list[str]


def _entries(
    profile: MasterProfileData, ids: set[str], facts: dict[str, str]
) -> dict[str, list[CvEntry]]:
    """The entries of the original CV, by kind of fact (`x`, `f`, `p`), with their lines."""
    children: dict[str, list[str]] = {}
    for x in profile.experiences:
        children[x.id] = [line.id for line in x.achievements]
    for e in profile.education:
        children[e.id] = [line.id for line in e.details]
    for p in profile.projects:
        children[p.id] = [line.id for line in p.achievements]
    described = {p.id: p.description for p in profile.projects if p.description.strip()}
    out: dict[str, list[CvEntry]] = {"x": [], "f": [], "p": []}
    for fact_id, entry in heads(profile, facts).items():
        if fact_id not in ids:
            continue
        if fact_id in described:
            entry.lines.append(CvLine(text=described[fact_id], fact_ids=[fact_id]))
        entry.lines += [
            CvLine(text=facts[child], fact_ids=[child])
            for child in children[fact_id]
            if child in ids
        ]
        out[fact_id[0]].append(entry)
    return out


def _items(facts: dict[str, str], ids: set[str], prefix: str) -> list[CvLine]:
    return [
        CvLine(text=text, fact_ids=[i])
        for i, text in facts.items()
        if i in ids and i[0] == prefix and i[1:].isdigit()
    ]


def base_content(profile: MasterProfileData, order: Sequence[SectionKey]) -> CvContent:
    """The original CV: the facts that came from the CV (`in_cv`), in the order of the template's
    sections (`order`), each line with its `fact_id`. A section that is empty, or that the
    template does not provide, does not appear."""
    ids = in_cv(profile)
    facts = facts_of(profile)
    entries = _entries(profile, ids, facts)
    content: dict[SectionKey, tuple[list[CvEntry], list[CvLine]]] = {
        "summary": ([], _items(facts, ids, "s")),
        "experience": (entries["x"], []),
        "education": (entries["f"], []),
        "skills": ([], _items(facts, ids, "c")),
        "projects": (entries["p"], []),
        "languages": ([], _items(facts, ids, "l")),
        "links": ([], _items(facts, ids, "k")),
    }
    title = profile.title
    identity = profile.identity
    return CvContent(
        name=identity.name,
        headline=title.text if title is not None and title.id in ids else None,
        contact=[value for value in (identity.email, identity.phone, identity.location) if value],
        sections=[
            CvSection(
                key=key, title=SECTION_TITLES[key], entries=content[key][0], items=content[key][1]
            )
            for key in dict.fromkeys(order)
            if content[key][0] or content[key][1]
        ],
    )


def apply_with_report(
    base: CvContent, profile: MasterProfileData, accepted: Sequence[Proposal]
) -> Applied:
    """`apply_modifications` and the ignored references. Order of application: remove, rewrite,
    add, move (within a kind, the order received). `base` is not modified."""
    composer = Composer(base, profile)
    ordered = sorted(accepted, key=lambda p: _ACTION_ORDER[p.action])
    ignored = [p.ref for p in ordered if not composer.apply(p)]
    logger.info(
        "CV composed: %d change(s) applied, %d ignored",
        len(ordered) - len(ignored),
        len(ignored),
    )
    return Applied(composer.content, ignored)


def apply_modifications(
    base: CvContent, profile: MasterProfileData, accepted: Sequence[Proposal]
) -> CvContent:
    """The targeted CV: `base` and the accepted changes. `rewrite` replaces the text of the
    line `target`; `add` adds the profile's fact `target` (text `after`) in its section, at its
    place in the profile; `remove` removes `target`; `move` places the section `section` before the
    section `after`. An absent target is ignored (`apply_with_report` counts it)."""
    return apply_with_report(base, profile, accepted).content
