"""`module_prompt` : la fiche du module, avec les API anciennes à ne montrer qu'en encadré."""

from dataclasses import replace

from app.agents.nodes.lesson_common import brief_of, module_prompt
from app.agents.tools.lesson_port import ModuleBrief

BRIEF = ModuleBrief(
    module_id="m1",
    program_id="p1",
    title="Appeler un modèle",
    skills=("LangChain",),
    prerequisites=(),
    week_rank=1,
    week_theme="Modèles et messages",
    goal_text="Devenir AI engineer",
    language="fr",
    seed_urls=(),
)


def test_prompt_without_legacy_has_no_legacy_line() -> None:
    assert "Reading older code" not in module_prompt(BRIEF)


def test_prompt_with_legacy_asks_for_a_boxed_mention_only() -> None:
    text = module_prompt(replace(BRIEF, legacy=("LLMChain", "LCEL")))
    assert "Legacy APIs in this chapter: LLMChain, LCEL" in text
    rule = text.rsplit("\n\n", 1)[
        1
    ]  # la règle suit l'encadré non fiable, elle n'en fait pas partie
    assert '"Reading older code"' in rule and "LLMChain" not in rule
    assert "Markdown blockquote" in rule and "Recommend current APIs" in rule


def test_brief_survives_the_state_round_trip() -> None:
    from dataclasses import asdict

    state = {"brief": asdict(replace(BRIEF, legacy=("LLMChain",)))}
    assert brief_of(state).legacy == ("LLMChain",)  # type: ignore[arg-type]
    old = {k: v for k, v in asdict(BRIEF).items() if k != "legacy"}
    assert brief_of({"brief": old}).legacy == ()  # type: ignore[arg-type]
