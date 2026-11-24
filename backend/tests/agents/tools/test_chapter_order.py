import pytest
from pydantic import ValidationError

from app.agents.tools.plan_schema import PlanDraft


def plan_with_chapters() -> dict[str, object]:
    task = {
        "title": "Expliquer la recherche",
        "type": "read",
        "minutes": 30,
        "done_criterion": "Écrire un exemple",
    }
    first = {
        "title": "Recherche par similarité",
        "skills": ["Recherche"],
        "introduces": [{"name": "Similarité cosinus", "definition": "Mesure d’orientation."}],
        "requires": [],
        "tasks": [task],
    }
    second = {
        "title": "Recherche de documents",
        "skills": ["Recherche"],
        "introduces": [],
        "requires": [" similarité   COSINUS "],
        "tasks": [task],
    }
    return {
        "title": "De la recherche aux agents",
        "skills": [{"name": "Recherche", "domain": "Recherche"}],
        "weeks": [
            {
                "theme": "Fondations",
                "objective": "Comprendre la recherche",
                "deliverable": "Démonstration",
                "modules": [first, second],
            }
        ],
    }


def test_chapter_prerequisites_and_definitions_survive_serialization() -> None:
    draft = PlanDraft.model_validate(plan_with_chapters())
    first, second = draft.model_dump()["weeks"][0]["modules"]
    assert first["introduces"][0]["name"] == "Similarité cosinus"
    assert second["requires"] == ["similarité   COSINUS"]


def test_prerequisite_first_appearing_in_current_chapter_is_refused() -> None:
    draft = plan_with_chapters()
    weeks = draft["weeks"]
    assert isinstance(weeks, list)
    first, second = weeks[0]["modules"]
    second["introduces"] = first["introduces"]
    first["introduces"] = []

    with pytest.raises(ValidationError, match="chapitre 2.*chapitre précédent"):
        PlanDraft.model_validate(draft)
