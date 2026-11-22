"""Les procès et les verdicts sont rattachés au propriétaire du projet."""

from fastapi import FastAPI

from app.db.base import new_id
from app.db.models.code_trial import CodeTrial
from tests.features.code_trial.test_trial import SOURCE, VERDICT, prepare_project
from tests.isolation.conftest import Browser


async def test_code_trial_routes_are_isolated(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("procureur@example.test")
    other = await google_client_factory("avocat@example.test")
    project, version = await prepare_project(owner)
    user = (await owner.get("/api/v1/auth/me")).json()["id"]
    tid = new_id()
    async with google_app.state.session_factory() as db:
        db.add(
            CodeTrial(
                id=tid,
                user_id=user,
                ide_session_id=project.rsplit("/", 1)[-1],
                session_id=new_id(),
                title="Projet d’un autre compte",
                files_version=version,
                snapshot=SOURCE,
            )
        )
        await db.commit()
    root = f"{project}/code-trials"
    assert (await owner.get(f"{root}/{tid}")).status_code == 200
    for response in (
        await other.get(root),
        await other.post(root),
        await other.get(f"{root}/{tid}"),
        await other.put(f"{root}/{tid}/verdict", json=VERDICT),
    ):
        assert response.status_code == 404
        assert "Projet d’un autre compte" not in response.text
