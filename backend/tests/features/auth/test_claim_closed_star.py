"""Revue finale 9.R (B-I1) : avec `ALLOWED_EMAILS=*` aucune reprise n'est proposée, mais le premier
compte Google ferme quand même la reprise : une liste nommée plus tard ne la rouvre pas."""

import httpx
from sqlalchemy import select

from app.db.models.accounts import UserSettingsRow
from app.features.account.schemas import DELETE_CONFIRMATION
from app.features.auth.repository import UserRepository
from tests.features.auth.claim_support import Factory, seed_local_space
from tests.features.auth.support import CAMILLE, FRONT, FakeGoogle, sign_in


async def test_first_account_without_an_offer_closes_the_claim(
    google_client: httpx.AsyncClient, google: FakeGoogle, db_session_factory: Factory
) -> None:
    local_id = await seed_local_space(db_session_factory)
    back = await sign_in(google_client, google, CAMILLE)
    assert back.headers["location"] == f"{FRONT}/"
    r = await google_client.post("/api/v1/account/delete", json={"confirm": DELETE_CONFIRMATION})
    assert r.status_code == 204
    async with db_session_factory() as db:
        row = (
            await db.execute(select(UserSettingsRow).where(UserSettingsRow.user_id == local_id))
        ).scalar_one()
        assert row.data["local_claim_closed"] is True
        assert (
            await UserRepository(db).attach_identity(local_id, "s", "e@example.org", "E") is False
        )
