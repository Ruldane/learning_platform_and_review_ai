"""`gap` trigger of the `replan` flow ("Add to schedule", SPEC F8, D123), without side effect:
the Strategist's rights, re-requests and cleaning of the draft.

With `gap`, the option is fixed: additions only (`ReplanAdds`, D105 (2)). A proposed removal is
ignored (the schema has no `drop`, preflight G12); each addition goes into the target module
`m0` ("Skills from postings") and names a skill from the list, in its title or its completion
criterion: otherwise it is requested again, then removed. The other triggers keep the rights of
their option (`replan_steps`). A `gap` context is recognized by its skills (`ctx.skills`)."""

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
    """The schema of the rights: additions only with `gap`, otherwise the option's."""
    return ReplanAdds if is_gap(ctx) else schema_for(option)


def draft_of(found: ReplanSummary, option: ReplanOption | None, ctx: ReplanContext) -> ReplanDraft:
    """The complete draft; with `gap`, additions only, all in `m0`."""
    if not is_gap(ctx):
        return to_draft(found, option)
    adds = [t.model_copy(update={"module": GAP_MODULE_REF}) for t in getattr(found, "add", [])]
    return ReplanDraft(summary=found.summary, add=adds)


def unnamed(draft: ReplanDraft, ctx: ReplanContext) -> list[int]:
    """Ranks (1...) of the additions that name no skill from the list (`gap` only)."""
    if not is_gap(ctx):
        return []
    return [n for n, task in enumerate(draft.add, start=1) if not skills_named(task, ctx.skills)]


def unnamed_text(ranks: list[int]) -> str:
    """The re-request only quotes ranks, never the postings' text (17.4)."""
    listed = ", ".join(f"n° {n}" for n in ranks)
    return (
        f"These added tasks name no skill from the list: {listed}. Each added task "
        "names, in its title or its completion criterion, a skill from the list exactly as "
        "written there. Answer again."
    )


def problem_text(draft: ReplanDraft, ctx: ReplanContext) -> str | None:
    """What to ask the model again: unknown references first, then additions without a
    skill; `None` if the draft is good."""
    unknown = unknown_refs(draft, ctx)
    if unknown:
        return unknown_text(unknown)
    ranks = unnamed(draft, ctx)
    return unnamed_text(ranks) if ranks else None


def cleaned(draft: ReplanDraft, ctx: ReplanContext) -> tuple[ReplanDraft, int]:
    """The draft without unknown references or skill-less additions, and the number removed."""
    known = without_unknown(draft, ctx)
    bad = set(unnamed(known, ctx))
    kept = [task for n, task in enumerate(known.add, start=1) if n not in bad]
    out = ReplanDraft(summary=known.summary, drop=known.drop, add=kept)
    return out, len(draft.drop) + len(draft.add) - len(out.drop) - len(out.add)
