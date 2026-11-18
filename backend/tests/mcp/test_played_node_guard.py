"""Toute nouvelle utilisation du modèle dans un nœud demande un essai en mode joué."""

import ast
from collections import Counter
from pathlib import Path

NODES = Path(__file__).resolve().parents[2] / "app" / "agents" / "nodes"

# Les appels partagent le fournisseur de session, y compris les helpers de plusieurs nœuds.
# Ce garde signale les nouveaux appels. Les tests de parcours vérifient les rendus et les écritures.
AUDITED = {
    "analyst": ("_ask_analysis", "_ask_matches"),
    "analyst_radar": ("_ask",),
    "archivist": ("extract",),
    "archivist_capture": ("digest",),
    "archivist_profile": ("extract",),
    "committee.common": ("persona_call",),
    "committee.synthesis": ("synthesis",),
    "debate_turn": ("turn",),
    "demo_turn": ("play_turn",),
    "designer": ("_copy", "ask_spec"),
    "examiner": ("_ask_quiz", "_ask_grades"),
    "exercise_writer.node": ("write",),
    "interviewer.debrief": ("_written",),
    "interviewer.plan": ("plan",),
    "interviewer.turn": ("_decide",),
    "moderator": ("frame",),
    "moderator_brief": ("advise",),
    "moderator_rounds": ("_ask",),
    "practitioner.brief": ("write",),
    "practitioner.drafts": ("_model",),
    "practitioner.evaluate": ("evaluate",),
    "professor.node": ("teach",),
    "review_common": ("ask_proposals",),
    "review_confront": ("_ask", "_reask"),
    "scout.assess": ("judge",),
    "scout.brief_resource": ("find_resource",),
    "scout.company": ("_brief",),
    "scout.dossier": ("_ask",),
    "scout.gather": ("plan",),
    "scout.people": ("_ask",),
    "scout.radar": ("_require_model",),
    "scout.resources": ("_ask",),
    "scribe": ("_valid_draft", "minutes"),
    "strategist.plan": ("_write",),
    "strategist.propose": ("_draft",),
    "strategist.replan": ("_write",),
    "tracker.intake": ("_read",),
    "tracker.pieces": ("write",),
    "tutor.models": ("ask_tutor",),
    "verifier.verify": ("_facts",),
    "writer": ("write",),
}


def calls_in(tree: ast.AST, function: str = "") -> Counter[str]:
    found: Counter[str] = Counter()
    if isinstance(tree, ast.FunctionDef | ast.AsyncFunctionDef):
        function = tree.name
    if (
        isinstance(tree, ast.Call)
        and isinstance(tree.func, ast.Attribute)
        and tree.func.attr == "get_chat_model"
    ):
        found[function] += 1
    for child in ast.iter_child_nodes(tree):
        found.update(calls_in(child, function))
    return found


def test_new_model_calls_require_played_coverage() -> None:
    actual = {}
    for path in sorted(NODES.rglob("*.py")):
        found = calls_in(ast.parse(path.read_text(encoding="utf-8")))
        if found:
            module = ".".join(path.relative_to(NODES).with_suffix("").parts)
            actual[module] = found
    assert actual == {module: Counter(functions) for module, functions in AUDITED.items()}
