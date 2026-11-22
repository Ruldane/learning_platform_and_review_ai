import json

from app.agents.tools.paper_lab_port import ExperimentDraft
from app.features.paper_lab.service.notebooks import notebook_files


def test_notebook_preserves_reference_and_measurable_experiment() -> None:
    url = "https://articles.exemple.org/regression"
    result = "La pente estimée vaut 2,0 sur les données générées."
    draft = ExperimentDraft(
        method="Comparer la pente calculée sur trois points définis.",
        code="points = [(1, 2), (2, 4), (3, 6)]\nprint(points[2][1] / points[2][0])",
        expected=result,
    )

    files = notebook_files(url, draft)
    notebook = json.loads(files["experience.ipynb"])
    intro, experiment = notebook["cells"]
    assert notebook["nbformat"] == 4
    assert url in intro["source"] and result in intro["source"]
    assert experiment["cell_type"] == "code"
    assert experiment["source"] == draft.code
    assert experiment["outputs"] == [] and experiment["execution_count"] is None
    assert files["main.py"].strip() == draft.code
