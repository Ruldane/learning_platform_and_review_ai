"""Composition du CV ciblé par le code (SPEC 5.3, critère 18.3) : le modèle ne rédige jamais le CV.
Le contenu part des faits du CV d'origine (`base_content`), puis reçoit les modifications
acceptées (`apply_modifications`). Chaque ligne porte les identifiants des faits du profil dont
elle vient : aucune ligne sans fait.

Le module ne juge pas : le contrôle contre le profil (`cv_validator`) et la décision de
l'utilisatrice se font avant. Il refuse seulement d'écrire ce qu'il ne sait pas placer : une cible
absente du contenu ou du profil est ignorée, comptée, et rendue à l'appelant."""

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
    """Le contenu composé et les références des modifications ignorées (cible introuvable)."""

    content: CvContent
    ignored: list[str]


def _entries(
    profile: MasterProfileData, ids: set[str], facts: dict[str, str]
) -> dict[str, list[CvEntry]]:
    """Les entrées du CV d'origine, par genre de fait (`x`, `f`, `p`), avec leurs lignes."""
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
    """Le CV d'origine : les faits venus du CV (`in_cv`), dans l'ordre des sections du gabarit
    (`order`), chaque ligne avec son `fact_id`. Une section vide, ou que le gabarit ne prévoit
    pas, n'apparaît pas."""
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
    """`apply_modifications` et les références ignorées. Ordre d'application : remove, rewrite,
    add, move (à l'intérieur d'un genre, l'ordre reçu). `base` n'est pas modifié."""
    composer = Composer(base, profile)
    ordered = sorted(accepted, key=lambda p: _ACTION_ORDER[p.action])
    ignored = [p.ref for p in ordered if not composer.apply(p)]
    logger.info(
        "CV composé : %d modification(s) appliquée(s), %d ignorée(s)",
        len(ordered) - len(ignored),
        len(ignored),
    )
    return Applied(composer.content, ignored)


def apply_modifications(
    base: CvContent, profile: MasterProfileData, accepted: Sequence[Proposal]
) -> CvContent:
    """Le CV ciblé : `base` et les modifications acceptées. `rewrite` remplace le texte de la
    ligne `target` ; `add` ajoute le fait `target` du profil (texte `after`) dans sa section, à sa
    place dans le profil ; `remove` retire `target` ; `move` place la section `section` avant la
    section `after`. Une cible absente est ignorée (`apply_with_report` la compte)."""
    return apply_with_report(base, profile, accepted).content
