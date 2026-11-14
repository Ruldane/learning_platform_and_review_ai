"""Déclencheur `gap` du parcours `replan` (« Ajouter au planning », SPEC F8, D123), sans effet de
bord : droits du Stratège, re-demandes et nettoyage du brouillon.

Avec `gap`, l'option est fixe : ajouts seuls (`ReplanAdds`, D105 (2)). Un retrait proposé est
ignoré (le schéma n'a pas de `drop`, preflight G12) ; chaque ajout va dans le module cible `m0`
(« Compétences des offres ») et nomme une compétence de la liste, dans son titre ou son critère
de fin : sinon il est redemandé, puis retiré. Les autres déclencheurs gardent les droits de leur
option (`replan_steps`). Un contexte `gap` se reconnaît à ses compétences (`ctx.skills`)."""

from app.agents.nodes.strategist.replan_steps import (
    schema_for,
    to_draft,
    unknown_refs,
    unknown_text,
    without_unknown,
)
from app.agents.tools.replan_port import (
    GAP_MODULE_REF,
    ReplanAdds,
    ReplanContext,
    ReplanDraft,
    ReplanSummary,
    skills_named,
)
from app.agents.tools.study_schema import ReplanOption


def is_gap(ctx: ReplanContext) -> bool:
    return bool(ctx.skills)


def schema_of(option: ReplanOption | None, ctx: ReplanContext) -> type[ReplanSummary]:
    """Le schéma des droits : ajouts seuls avec `gap`, sinon celui de l'option."""
    return ReplanAdds if is_gap(ctx) else schema_for(option)


def draft_of(found: ReplanSummary, option: ReplanOption | None, ctx: ReplanContext) -> ReplanDraft:
    """Le brouillon complet ; avec `gap`, les ajouts seuls, tous dans `m0`."""
    if not is_gap(ctx):
        return to_draft(found, option)
    adds = [t.model_copy(update={"module": GAP_MODULE_REF}) for t in getattr(found, "add", [])]
    return ReplanDraft(summary=found.summary, add=adds)


def unnamed(draft: ReplanDraft, ctx: ReplanContext) -> list[int]:
    """Rangs (1…) des ajouts qui ne nomment aucune compétence de la liste (`gap` seul)."""
    if not is_gap(ctx):
        return []
    return [n for n, task in enumerate(draft.add, start=1) if not skills_named(task, ctx.skills)]


def unnamed_text(ranks: list[int]) -> str:
    """La re-demande ne cite que des rangs, jamais le texte des offres (17.4)."""
    listed = ", ".join(f"n° {n}" for n in ranks)
    return (
        f"Ces tâches ajoutées ne nomment aucune compétence de la liste : {listed}. Chaque tâche "
        "ajoutée nomme, dans son titre ou son critère de fin, une compétence de la liste telle "
        "qu'elle y est écrite. Réponds de nouveau."
    )


def problem_text(draft: ReplanDraft, ctx: ReplanContext) -> str | None:
    """Ce qu'il faut redemander au modèle : références inconnues d'abord, puis ajouts sans
    compétence ; `None` si le brouillon est bon."""
    unknown = unknown_refs(draft, ctx)
    if unknown:
        return unknown_text(unknown)
    ranks = unnamed(draft, ctx)
    return unnamed_text(ranks) if ranks else None


def cleaned(draft: ReplanDraft, ctx: ReplanContext) -> tuple[ReplanDraft, int]:
    """Le brouillon sans référence inconnue ni ajout sans compétence, et le nombre retiré."""
    known = without_unknown(draft, ctx)
    bad = set(unnamed(known, ctx))
    kept = [task for n, task in enumerate(known.add, start=1) if n not in bad]
    out = ReplanDraft(summary=known.summary, drop=known.drop, add=kept)
    return out, len(draft.drop) + len(draft.add) - len(out.drop) - len(out.add)
