"""Compétences de January (SPEC 4.2, 13.4 ; D6, D7) : référentiel du Stratège (compétences,
prérequis) et niveaux, qui ne baissent jamais. Le commit appartient à l'appelant."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.skills import Evidence, normalize_skill_name, read_evidence
from app.db.models.skills import LEVEL_ORDER, SkillLevel
from app.features.skills.repository import (
    SkillEdgeRepository,
    SkillRepository,
    UserSkillRepository,
)

__all__ = ["SkillLevel", "SkillsService", "higher_level"]

EVIDENCE_MAX = 20  # preuves gardées par compétence (les plus récentes)


def higher_level(a: SkillLevel, b: SkillLevel) -> SkillLevel:
    return a if LEVEL_ORDER.index(a) >= LEVEL_ORDER.index(b) else b


def _proof_key(item: Evidence) -> tuple[str, str | None]:
    """Clé de dédoublonnage : (genre, référence) ; sans référence, le libellé fait foi."""
    return (item["kind"], item["ref_id"] if item["ref_id"] is not None else item["label"])


def _with_proof(raw: Sequence[Any], proof: Evidence) -> list[Evidence]:
    """Les preuves relues, plus `proof` si son couple (genre, référence) manque (la première
    gagne : un rejeu ne réécrit rien), au plus `EVIDENCE_MAX` des plus récentes."""
    kept = read_evidence(raw)
    if all(_proof_key(item) != _proof_key(proof) for item in kept):
        kept.append(proof)
    return kept[-EVIDENCE_MAX:]


def _as_level(value: str) -> SkillLevel:
    for level in LEVEL_ORDER:
        if level == value:
            return level
    return "declare"


class SkillsService:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._skills = SkillRepository(db, user_id)
        self._edges = SkillEdgeRepository(db, user_id)
        self._levels = UserSkillRepository(db, user_id)

    async def upsert_catalog(
        self, skills: Sequence[SkillDraft], edges: Sequence[EdgeDraft]
    ) -> dict[str, str]:
        """Compétences (dédoublonnées par nom normalisé) et liens de prérequis ; rend
        `nom normalisé → id`. Un lien dont un bout est inconnu, ou une boucle, est ignoré."""
        for skill in skills:
            norm = normalize_skill_name(skill.name)
            if norm:
                await self._skills.ensure(skill.name, norm, skill.domain, list(skill.synonyms))
        names = {normalize_skill_name(s.name) for s in skills} - {""}
        rows = await self._skills.by_norm(names)
        ids = {norm: row.id for norm, row in rows.items()}
        for edge in edges:
            before = ids.get(normalize_skill_name(edge.before))
            after = ids.get(normalize_skill_name(edge.after))
            if before is not None and after is not None and before != after:
                await self._edges.ensure(before, after)
        await self._db.flush()
        return ids

    async def _skill_ids(self, names: Sequence[str]) -> dict[str, tuple[str, str]]:
        """`nom normalisé → (id, nom affiché)`, compétences créées au besoin (sans domaine)."""
        wanted: dict[str, str] = {}
        for name in names:
            norm = normalize_skill_name(name)
            if norm and norm not in wanted:
                wanted[norm] = name.strip()[:120]
        for norm, name in wanted.items():
            await self._skills.ensure(name, norm, None, [])
        rows = await self._skills.by_norm(list(wanted))
        return {norm: (row.id, row.name) for norm, row in rows.items()}

    async def raise_levels(
        self, names: Sequence[str], level: SkillLevel, evidence: Evidence
    ) -> list[tuple[str, SkillLevel]]:
        """Monte chaque compétence à `level` au moins (jamais plus bas) et note la preuve,
        dédoublonnée par (genre, référence) ;
        rend `(nom, nouveau niveau)` des seuls niveaux changés (créés compris)."""
        skills = await self._skill_ids(names)
        ids = [skill_id for skill_id, _ in skills.values()]
        before = await self._levels.for_skills(ids)
        for skill_id in ids:
            if skill_id not in before:  # nouvelle : créée au niveau voulu (une course : rien)
                await self._levels.ensure(skill_id, level)
        rows = await self._levels.for_skills(ids)
        changed: list[tuple[str, SkillLevel]] = []
        for skill_id, name in skills.values():
            row = rows[skill_id]
            old = before.get(skill_id)
            current = _as_level(old.level) if old is not None else None
            target = higher_level(_as_level(row.level), level)
            row.evidence = list(_with_proof(row.evidence, evidence))
            row.level = target
            if target != current:
                changed.append((name, target))
        await self._db.flush()
        return changed

    async def levels_of(self, names: Sequence[str]) -> list[tuple[str, SkillLevel]]:
        """`(nom affiché, niveau)` actuel de chacune de ces compétences qui a un niveau, une
        fois par nom normalisé (pour refléter les niveaux dans la mémoire)."""
        norms = [norm for norm in dict.fromkeys(map(normalize_skill_name, names)) if norm]
        rows = await self._skills.by_norm(norms)
        levels = await self._levels.for_skills([row.id for row in rows.values()])
        return [
            (rows[norm].name, _as_level(levels[rows[norm].id].level))
            for norm in norms
            if norm in rows and rows[norm].id in levels
        ]

    async def known_levels(self) -> dict[str, SkillLevel]:
        """`nom normalisé → niveau` de chaque compétence connue de January."""
        return {norm: _as_level(level) for norm, level in await self._levels.levels()}
