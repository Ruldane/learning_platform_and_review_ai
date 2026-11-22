"""Le professeur résout les chemins imbriqués sans transmettre tous les fichiers."""

from app.agents.nodes.professor.context import build_context, error_place
from app.agents.tools.ide_port import TeachInputs


def test_traceback_prefers_the_most_specific_project_path() -> None:
    output = '  File "/work/essai/src/calcul.py", line 4, in <module>'
    assert error_place(output, {"calcul.py", "src/calcul.py"}) == ("src/calcul.py", 4)


def test_question_can_target_another_project_file_without_sending_its_neighbors() -> None:
    files = {"main.py": "Autre texte", "src/calcul.py": "x = 2", "notes.md": "Retrait"}
    inputs = TeachInputs("Projet", None, files, "main.py", False, "guide", None)
    context = build_context(inputs, file_path="main.py", question="Explique `src/calcul.py`.")
    assert context.path == "src/calcul.py"
    assert "x = 2" in context.window and "Autre texte" not in context.window
    assert context.project_paths == ["main.py", "notes.md", "src/calcul.py"]
