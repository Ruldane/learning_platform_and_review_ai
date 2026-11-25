"""New model calls in agent nodes require a test with a played session."""

import ast
from collections import Counter
from pathlib import Path

NODES = Path(__file__).resolve().parents[2] / "app" / "agents" / "nodes"

# Calls share the session's model provider, including helpers used by multiple nodes.
# The played tests cover conversation modes in test_played_explanations and test_training_modes.
AUDITED = {
    "analyst": ("_ask_analysis", "_ask_matches"),
    "analyst_radar": ("_ask",),
    "archivist": ("extract",),
    "archivist_capture": ("digest",),
    "archivist_profile": ("extract",),
    "committee.common": ("role_call",),
    "committee.synthesis": ("synthesis",),
    "conversation": ("_classroom_reply", "reply"),
    "debate_turn": ("turn",),
    "demo_turn": ("play_turn",),
    "designer": ("_copy", "ask_spec"),
    "examiner": ("_ask_quiz", "_ask_grades"),
    "exercise_writer.node": ("write",),
    "feynman": ("assess",),
    "interviewer.debrief": ("_written",),
    "interviewer.plan": ("plan",),
    "interviewer.system_design": ("review",),
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
