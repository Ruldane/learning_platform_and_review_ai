import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.accounts import User
from app.db.models.study import Flashcard
from tests.e2e.augmented_reader import DEFINITION, PASSAGE, seed_article, seed_glossary
from tests.sessions_support import act_as

API = "/api/v1/reading-stack"


async def test_reader_definitions_and_selected_cards_only_use_owned_content(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = app.state.local_user_id
    lesson_id = await seed_glossary(app, owner)
    article = await seed_article(app, owner)
    detail = (await client.get(f"{API}/{article}")).json()
    (annotation,) = detail["annotations"]
    assert annotation["definition"] == DEFINITION and annotation["lesson_id"] == lesson_id
    rendered = detail["text"].encode("utf-16-le")
    assert (
        rendered[annotation["start"] * 2 : annotation["end"] * 2].decode("utf-16-le")
        == "index inversé"
    )

    card_url = f"{API}/{article}/cards"
    assert (await client.post(card_url, json={"passage": "Un autre texte."})).status_code == 409
    assert (await client.post(card_url, json={"passage": PASSAGE})).json()["count"] == 1
    assert (await client.post(card_url, json={"passage": PASSAGE})).json()["count"] == 0
    async with app.state.session_factory() as db:
        card = (await db.execute(select(Flashcard).where(Flashcard.user_id == owner))).scalar_one()
        assert card.back == f"{PASSAGE}\n\nhttps://example.org/index"
        db.add(User(id="autre-lecture", user_id="autre-lecture"))
        await db.commit()

    act_as(app, "autre-lecture")
    other_article = await seed_article(app, "autre-lecture")
    assert (await client.get(f"{API}/{article}")).status_code == 404
    assert (await client.post(card_url, json={"passage": PASSAGE})).status_code == 404
    assert (await client.get(f"{API}/{other_article}")).json()["annotations"] == []
