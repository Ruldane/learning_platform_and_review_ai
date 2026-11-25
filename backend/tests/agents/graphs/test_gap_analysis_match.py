"""Rattachement des besoins de l'offre au référentiel de January (D121 n° 3, revue 6.5) : sur le
référentiel existant, niveaux montrés, identifiants plutôt que noms recopiés, jamais un nom
inventé ; les besoins sans rattachement n'entrent au référentiel qu'après."""

from app.agents.nodes.analyst_steps import MATCH_REQUEST
from tests.agents.graphs.gap_support import MakeGap, analyst
from tests.support.gap import (
    LEVELS,
    MATCHES,
    NEED_REFS,
    POSTING_ID,
    FakeGapStore,
    items_reply,
    known_refs,
    matches_reply,
)

LONG_NAME = "Conception et évaluation de pipelines RAG avec recherche hybride et réordonnancement"


def matched(store: FakeGapStore) -> dict[str, str | None]:
    return {m["need"]: m["known"] for m in store.gap[POSTING_ID]["matches"]}


async def test_need_matches_the_acquired_notion_not_a_new_homonym(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Revue 6.5, I2 : « RAG » se rattache à « Génération augmentée par recherche » (validé) ;
    le référentiel ne reçoit que les besoins restés sans rattachement, après."""
    run = await gap_runner()
    await run.wait_status("completed")
    assert matched(gap_store)["RAG"] == "Génération augmentée par recherche"
    assert "RAG" not in gap_store.levels
    assert gap_store.catalog_added == [
        "LangGraph",
        "Évaluation de RAG",
        "Intégration continue",
        "Anglais professionnel",
    ]
    [prompt] = run.prompts(MATCH_REQUEST)
    assert "RAG (required)" not in prompt.split("January's framework")[1].split("Reply")[0]
    assert "- k1: Recherche vectorielle (level: proven)" in prompt
    assert "Génération augmentée par recherche (level: validated)" in prompt
    assert "- k7: Kubernetes (level: no level)" in prompt
    assert "- n3: RAG (required)" in prompt and "- n8: Docker (preferred)" in prompt


async def test_second_posting_sees_needs_added_by_the_first(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    run = await gap_runner()
    await run.wait_status("completed")
    gap_store.gap.clear()
    second = await gap_runner(analyst(matches=[matches_reply(levels=gap_store.levels)]))
    await second.wait_status("completed")
    [prompt] = second.prompts(MATCH_REQUEST)
    assert "LangGraph (level: no level)" in prompt
    assert matched(gap_store)["LangGraph"] == "LangGraph"  # même nom : rattaché
    assert gap_store.catalog_added.count("LangGraph") == 1


async def test_long_referential_name_is_matched(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Revue 6.5, I1 : un nom du référentiel de 84 caractères (plafond 120) ne fait pas échouer
    le rattachement."""
    assert len(LONG_NAME) == 84
    levels = {LONG_NAME: "validated", **LEVELS}
    gap_store.levels = dict(levels)
    run = await gap_runner(
        analyst(matches=[matches_reply({**MATCHES, "RAG": LONG_NAME}, levels=levels)])
    )
    await run.wait_status("completed")
    assert matched(gap_store)["RAG"] == LONG_NAME and gap_store.gaps[POSTING_ID].score == 62


async def test_suffixed_identifiers_never_lose_a_match(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Revue 6.5, I3 : un identifiant suivi de son annotation (« n3 (obligatoire) »,
    « k2 (niveau : validé) ») ou un nom suivi de son niveau garde son rattachement."""
    refs = known_refs()
    items = [
        {"need": "n3 (obligatoire)", "known": f"{refs['Génération augmentée par recherche']} "
         "(niveau : validé)"},
        {"need": "N1 : Python", "known": "Python (niveau : validé)"},
        {"need": "n5", "known": "agents llm"},
    ]  # fmt: skip
    run = await gap_runner(analyst(matches=[items_reply(items)]))
    await run.wait_status("completed")
    found = matched(gap_store)
    assert found["RAG"] == "Génération augmentée par recherche"
    assert found["Python"] == "Python" and found["Agents conversationnels"] == "Agents LLM"


async def test_unknown_referential_name_becomes_none(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    items = [
        {"need": NEED_REFS["Intégration continue"], "known": "Jenkins"},  # hors référentiel
        {"need": NEED_REFS["LangGraph"], "known": "k99"},  # identifiant inconnu
        {"need": "n42", "known": "k1"},  # besoin inconnu
        {"need": NEED_REFS["Évaluation de RAG"], "known": known_refs()["Kubernetes"]},
    ]
    run = await gap_runner(analyst(matches=[items_reply(items)]))
    await run.wait_status("completed")
    found = matched(gap_store)
    assert found["Intégration continue"] is None and found["LangGraph"] is None
    assert found["Évaluation de RAG"] == "Kubernetes"  # au référentiel (sans niveau) : gardé
    assert len(found) == 10 and found["Python"] == "Python"  # oublié : même nom


async def test_missing_answers_fall_back_to_same_name(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Un besoin oublié ou laissé à `null` dont le nom figure tel quel au référentiel lui est
    rattaché ; une compétence désignée par son nom écrit autrement est ramenée à son écriture."""
    items = [
        {"need": NEED_REFS["Python"], "known": None},
        {"need": NEED_REFS["RAG"], "known": "génération augmentée par recherche"},
    ]
    run = await gap_runner(analyst(matches=[items_reply(items)]))
    await run.wait_status("completed")
    found = matched(gap_store)
    assert found["Python"] == "Python" and found["Docker"] == "Docker"
    assert found["RAG"] == "Génération augmentée par recherche"
    assert found["Agents conversationnels"] is None and len(found) == 10


async def test_empty_referential_matches_without_model_call(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    gap_store.levels = {}
    run = await gap_runner()
    await run.wait_status("completed")
    assert run.prompts(MATCH_REQUEST) == []
    assert all(known is None for known in matched(gap_store).values())
    assert gap_store.gaps[POSTING_ID].score == 0 and len(gap_store.catalog_added) == 10
