"""Contexte mémoire réutilisable (4.4) : acquis, décisions et documents proches de l'objectif."""

from app.agents.nodes.memory_context import load_memory_context
from app.agents.runtime.deps import GraphDeps
from tests.agents.tools.conftest import FakeGateway


async def test_load_memory_context_reads_skills_decisions_and_documents(
    emitted: list[dict[str, object]], deps: GraphDeps, gateway: FakeGateway
) -> None:
    context = await load_memory_context(deps, objective="apprendre Rust", agent="archivist")
    assert gateway.searches == [
        ("apprendre Rust", ("decision",), 8),
        ("apprendre Rust", ("document",), 8),
    ]
    assert [e["payload"]["tool"] for e in emitted if e["__tremplin_event__"] == "tool.called"] == [  # type: ignore[index]
        "memory_get_skills",
        "memory_search",
        "memory_search",
    ]
    prompt = context.as_prompt()
    assert "- Python — declare" in prompt and prompt.count("Mémoire — 3 fragment(s)") == 2
    assert context.skills.total == 1 and len(context.documents.hits) == 3
