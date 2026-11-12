"""Cas limites du retrait déterministe (relecture de eed6fb5, D97 n° 11) : abréviations et
décimaux au découpage, fragment ambigu ou trop court, sous-liste, code dans un élément, marqueur
après le point, contrôle après retrait. Pur, sans réseau ni modèle."""

import pytest

from app.agents.nodes.lesson_common import LessonSource
from app.agents.nodes.verifier import Pruned, in_scope, prune, still_cited
from app.agents.nodes.verifier import verify as verify_module
from tests.support.lessons import TITLE, lesson_markdown

KEEP_BEFORE = "Première phrase gardée sur le sujet [1]."
KEEP_AFTER = "Dernière phrase gardée sur le sujet [2]."


def _lesson(paragraph: str) -> str:
    """Leçon valide avec `paragraph` en tête de la section « Explication »."""
    head = "## Explication\n\n"
    return lesson_markdown(1400).replace(head, head + paragraph + "\n\n", 1)


@pytest.mark.parametrize(
    "sentence",
    [
        "Un framework web aide beaucoup, p. ex. Django pour les sites dynamiques [1].",
        "Les outils comptent Git, GitHub, etc. Python les pilote aussi très bien [1].",
        "La documentation le confirme, cf. Microsoft Learn pour les postes Windows [1].",
        "L'installateur de Python pèse env. 30 Mo sur le disque dur [1].",
        "Le langage a été créé par M. Van Rossum aux Pays-Bas en 1991 [1].",
        "Un framework web aide beaucoup, e.g. Django pour les sites dynamiques [1].",
        "Un éditeur suffit pour débuter, i.e. VS Code avec son extension Python [1].",
        "Il faut installer Python. ensuite on vérifie la version installée [1].",
        "Python 3.12 donne des messages d'erreur plus clairs que la 3.11 [1].",
    ],
    ids=["p-ex", "etc", "cf", "env", "M", "e-g", "i-e", "minuscule", "decimaux"],
)
def test_a_sentence_is_never_cut_at_an_abbreviation(sentence: str) -> None:
    lesson = _lesson(f"{KEEP_BEFORE} {sentence} {KEEP_AFTER}")
    claim = f"« {sentence.removesuffix(' [1].')} » : non sourcé."
    result = prune(lesson, [claim])
    assert (result.removed, result.unlocated) == (1, 0)
    assert f"{KEEP_BEFORE} {KEEP_AFTER}" in result.markdown
    assert still_cited(result.markdown, [claim]) == 0


def test_a_fragment_found_in_several_sentences_is_unlocated() -> None:
    lesson = _lesson(
        "Python sert à automatiser les tâches de bureau [1]. Bash sert à automatiser les "
        "tâches de bureau aussi [2]."
    )
    claim = "« sert à automatiser les tâches de bureau » : non sourcé."
    result = prune(lesson, [claim])
    assert (result.removed, result.unlocated, result.markdown) == (0, 1, lesson)
    assert in_scope(lesson, [claim]) == [claim]  # introuvable : gardée, donc l'échec motivé


def test_a_short_fragment_must_cover_most_of_its_sentence() -> None:
    long_one = (
        "Python est un langage lent mais très lisible et très répandu chez les débutants [1]."
    )
    lesson = _lesson(f"{KEEP_BEFORE} {long_one} Python est lent [2]. {KEEP_AFTER}")
    loose = "« langage lent mais » : trois mots sur quatorze."
    assert prune(lesson, [loose]).unlocated == 1
    tight = "« Python est lent » : la source ne compare pas les vitesses."
    result = prune(lesson, [tight])
    assert (result.removed, result.unlocated) == (1, 0)
    assert long_one in result.markdown and "Python est lent [2]." not in result.markdown


def test_a_marker_after_the_period_leaves_with_its_sentence() -> None:
    lesson = _lesson(
        f"{KEEP_BEFORE} Python est le langage le plus rapide du monde. [2] {KEEP_AFTER}"
    )
    result = prune(lesson, ["« Python est le langage le plus rapide du monde » : faux."])
    assert f"{KEEP_BEFORE} {KEEP_AFTER}" in result.markdown


def test_an_item_with_a_sub_list_is_removed_whole() -> None:
    items = (
        "- Python est compilé en code machine natif avant chaque exécution [1].\n"
        "  - Le compilateur s'appelle CPython [1].\n"
        "- Python est interprété par CPython [2]."
    )
    claim = "« Python est compilé en code machine natif avant chaque exécution » : faux."
    result = prune(_lesson(items), [claim])
    assert (result.removed, result.unlocated) == (1, 0)
    assert "compilé" not in result.markdown and "Le compilateur" not in result.markdown
    assert "- Python est interprété par CPython [2]." in result.markdown


def test_an_item_holding_code_is_never_removed() -> None:
    items = (
        "- Python s'installe en une seule commande sur tous les systèmes [1].\n\n"
        "  ```bash\n  winget install Python.Python.3.12\n  ```\n"
        "- Une autre étape bien sourcée [2]."
    )
    lesson = _lesson(items)
    claim = "« Python s'installe en une seule commande sur tous les systèmes » : non sourcé."
    result = prune(lesson, [claim])
    assert (result.removed, result.unlocated, result.markdown) == (0, 1, lesson)


def test_still_cited_sees_a_fragment_left_in_a_table() -> None:
    claim = "« Python est le langage le plus utilisé au monde » : non sourcé."
    table = (
        "| Langage | Remarque |\n| --- | --- |\n"
        "| Python | Python est le langage le plus utilisé au monde |"
    )
    lesson = _lesson(f"Python est le langage le plus utilisé au monde [1].\n\n{table}")
    result = prune(lesson, [claim])
    assert result.removed == 1 and still_cited(result.markdown, [claim]) == 1


def test_converge_fails_when_a_cited_fragment_is_still_there(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lesson = _lesson(f"Python est le langage le plus utilisé au monde [1]. {KEEP_AFTER}")
    claim = "« Python est le langage le plus utilisé au monde » : non sourcé."
    monkeypatch.setattr(verify_module, "prune", lambda md, _c: Pruned(md, 1, 0))
    sources: list[LessonSource] = []
    update, removed = verify_module._converge(lesson, TITLE, sources, [claim])
    assert removed == 0 and "draft" not in update
    assert update["problems"] == [
        "Retrait incomplet : 1 affirmation(s) non sourcée(s) encore dans la leçon."
    ]
