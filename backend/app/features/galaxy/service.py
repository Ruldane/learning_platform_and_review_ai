"""Galaxy data, computed on read for a single account."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.features.brain.service.note_graph import SyncedNote, synced_note_graph
from app.features.galaxy.schemas import GalaxyAction, GalaxyEdge, GalaxyNode, GalaxyView
from app.features.lessons.service.lessons import published_lesson_routes
from app.features.program.service.skill_modules import teaching_module_ids
from app.features.skills.service import learning_graph


def _note_nodes(notes: list[SyncedNote], chapters: set[str]) -> list[GalaxyNode]:
    result: list[GalaxyNode] = []
    for note in notes:
        chapter = next((key for key in note.lesson_ids if key in chapters), None)
        action = (
            GalaxyAction(kind="lesson", ref=chapter)
            if chapter is not None
            else GalaxyAction(kind="note", ref=note.id)
        )
        result.append(
            GalaxyNode(id=f"note:{note.id}", kind="note", title=note.title, action=action)
        )
    return result


def _note_edges(notes: list[SyncedNote], named_skills: dict[str, str]) -> list[GalaxyEdge]:
    edges: list[GalaxyEdge] = []
    for note in notes:
        origin = f"note:{note.id}"
        edges.extend(
            GalaxyEdge(source=origin, target=f"note:{key}", kind="reference")
            for key in note.linked_ids
        )
        for tag in note.tags:
            if skill_id := named_skills.get(normalize_skill_name(tag)):
                edges.append(GalaxyEdge(source=origin, target=skill_id, kind="topic"))
    return edges


async def read_galaxy(db: AsyncSession, user_id: str) -> GalaxyView:
    graph, target = await learning_graph(db, user_id)
    notes = await synced_note_graph(db, user_id)
    chapters = await published_lesson_routes(db, user_id)
    modules = await teaching_module_ids(db, user_id) if graph.nodes else {}
    gaps = {row.skill_id: max(0, row.gap) for row in target.rows} if target else {}
    named_skills: dict[str, str] = {}
    nodes = _note_nodes(notes, set(chapters.values()))
    for skill in graph.nodes:
        norm = normalize_skill_name(skill.name)
        key = f"skill:{skill.id}"
        named_skills[norm] = key
        chapter = next((chapters[key] for key in modules.get(norm, []) if key in chapters), None)
        nodes.append(
            GalaxyNode(
                id=key,
                kind="skill",
                title=skill.name,
                domain=skill.domain,
                level=skill.level,
                gap=gaps.get(skill.id),
                action=(
                    GalaxyAction(kind="lesson", ref=chapter)
                    if chapter
                    else GalaxyAction(kind="training", ref=skill.id)
                ),
            )
        )
    edges = _note_edges(notes, named_skills)
    edges.extend(
        GalaxyEdge(
            source=f"skill:{edge.before_id}", target=f"skill:{edge.after_id}", kind="prerequisite"
        )
        for edge in graph.edges
    )
    active = {node.id for node in nodes}
    unique = {
        (edge.source, edge.target, edge.kind): edge
        for edge in edges
        if edge.source in active and edge.target in active
    }
    return GalaxyView(
        nodes=nodes,
        edges=[unique[key] for key in sorted(unique)],
        target_label=target.target_label if target else None,
    )
