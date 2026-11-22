import httpx
from fastapi import FastAPI

from tests.features.error_atlas.support import (
    HYPOTHESIS,
    PROJECT_FINDING,
    QUIZ_FINDING,
    seed_evidence,
)

API = "/api/v1/error-atlas"


async def test_verified_errors_group_and_freeze_the_corrective_exercise(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    await seed_evidence(app)
    available = await client.get(f"{API}/evidence")
    assert available.status_code == 200, available.text
    evidence = {item["reference"]["kind"]: item for item in available.json()}
    assert set(evidence) == {"quiz", "project"}
    assert evidence["quiz"]["finding"] == QUIZ_FINDING
    assert evidence["project"]["finding"] == PROJECT_FINDING
    quiz = evidence["quiz"]["reference"]
    correction = await client.get(
        f"/api/v1/quizzes/{quiz['resource_id']}/attempts/{quiz['source_id']}"
    )
    assert correction.status_code == 200 and correction.json()["status"] == "graded"
    project = await client.get(
        f"/api/v1/projects/{evidence['project']['reference']['resource_id']}"
    )
    assert project.status_code == 200 and project.json()["evaluation"]["results"][0]["met"] is False
    first_action = {
        "reference": evidence["quiz"]["reference"],
        "hypothesis": HYPOTHESIS,
        "confidence": "low",
    }
    first = await client.post(f"{API}/observations", json=first_action)
    assert first.status_code == 201, first.text
    first_group = first.json()
    assert len(first_group["observations"]) == 1
    assert first_group["confidence"] == "low"
    assert (await client.post(f"{API}/observations", json=first_action)).json() == first_group

    second = await client.post(
        f"{API}/observations",
        json={
            "reference": evidence["project"]["reference"],
            "hypothesis": " valeurs  MANQUANTES ",
            "confidence": "high",
        },
    )
    assert second.status_code == 201, second.text
    combined = second.json()
    assert combined["id"] == first_group["id"]
    assert combined["label"] == HYPOTHESIS
    assert combined["confidence"] == "mixed"
    assert len(combined["observations"]) == 2

    await _assert_saved_exercise(client, combined["id"])


async def _assert_saved_exercise(client: httpx.AsyncClient, hypothesis_id: str) -> None:
    path = f"{API}/hypotheses/{hypothesis_id}/exercise"
    created = await client.post(path)
    assert created.status_code == 201, created.text
    exercise = created.json()
    assert len(exercise["steps"]) >= 2
    assert {item["finding"] for item in exercise["evidence"]} == {QUIZ_FINDING, PROJECT_FINDING}
    assert (await client.post(path)).json() == exercise
    assert (await client.get(API)).json()[0]["exercise"] == exercise


async def test_correct_answer_and_forged_project_revision_are_rejected(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    _, passed_question = await seed_evidence(app)
    evidence = {
        row["reference"]["kind"]: row["reference"]
        for row in (await client.get(f"{API}/evidence")).json()
    }
    for ref in (
        {**evidence["quiz"], "item_id": passed_question},
        {**evidence["project"], "source_id": "ancien-rendu"},
    ):
        response = await client.post(
            f"{API}/observations",
            json={
                "reference": ref,
                "hypothesis": HYPOTHESIS,
                "confidence": "medium",
            },
        )
        assert response.status_code == 404
    assert (await client.get(API)).json() == []
