"""Le début de prompt fixe du professeur porte la marque de cache d'Anthropic (10.A3) ; sans la
marque (ou chez un autre fournisseur), rien ne change. Aucun réseau : la charge de la requête est
construite sans être envoyée."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.professor.prompt import prefix_of
from app.agents.tools.ide_port import TeachInputs
from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.base import CACHE_PREFIX_KEY

INPUTS = TeachInputs("Titre", "Énoncé", {"main.py": "x = 1\n"}, "main.py", False, "guide", None)


def payload(*messages: SystemMessage | HumanMessage) -> dict[str, object]:
    model = AnthropicProvider().build("claude-test", "clé-factice")
    return model._get_request_payload(list(messages))  # type: ignore[attr-defined, no-any-return]


def test_anthropic_prefix_carries_cache_marker() -> None:
    prefix = prefix_of(INPUTS)
    sent = payload(prefix, HumanMessage("La demande qui change."))
    system = sent["system"]
    assert isinstance(system, list) and len(system) == 1
    assert system[0]["text"] == prefix.content and system[0]["cache_control"] == {
        "type": "ephemeral"
    }
    assert sent["messages"] == [{"role": "user", "content": "La demande qui change."}]


def test_unmarked_system_message_is_left_alone() -> None:
    sent = payload(SystemMessage("Consignes"), HumanMessage("Bonjour"))
    assert sent["system"] == "Consignes"
    marked_other = SystemMessage("Consignes", additional_kwargs={CACHE_PREFIX_KEY: False})
    assert payload(marked_other, HumanMessage("Bonjour"))["system"] == "Consignes"


def test_prefix_depends_only_on_the_exercise_and_the_style() -> None:
    a = prefix_of(INPUTS)
    other_code = TeachInputs(
        "Titre", "Énoncé", {"main.py": "y = 2\n"}, "main.py", True, "guide", None, notes=[]
    )
    assert a.content == prefix_of(other_code).content  # ni le code ni la réussite n'y entrent
    pair = TeachInputs("Titre", "Énoncé", {"main.py": ""}, "main.py", False, "pair", None)
    assert a.content != prefix_of(pair).content
