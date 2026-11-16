"""Le curseur `(at, id)` du fil (D163) : des événements au même instant ne se perdent ni à la
coupure d'une page ni à la frontière d'une relecture ; une source en panne est écartée ; la capture
de January n'est pas un travail de fond."""

import logging

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.service import feed
from app.features.memory.service.captured import CAPTURE_AUTHOR, CAPTURE_REASON, reflect_reason
from tests.features.activity.support import Env, add_brief, add_write, hours
from tests.features.activity.support import page as _page


async def test_ties_are_kept_across_pages(env: Env) -> None:
    """Cinq écritures au même instant plus une plus ancienne : des pages de deux ne perdent ni ne
    répètent aucun événement."""
    ids = [await add_write(env, hours(3), title=f"Ex æquo {n}") for n in range(5)]
    older = await add_write(env, hours(1), title="Plus ancien")
    seen: list[str] = []
    current = await _page(env, limit=2)
    while current.items:
        seen += [item.id for item in current.items]
        last = current.items[-1]
        current = await _page(env, before=last.at, before_id=last.id, limit=2)
    assert len(seen) == 6 and set(seen) == {f"memory:{i}:create" for i in [*ids, older]}
    assert seen[:5] == sorted(seen[:5], reverse=True) and seen[5] == f"memory:{older}:create"


async def test_after_cursor_keeps_a_tie_that_arrives_late(env: Env) -> None:
    """La relecture `after = latest_at` rend un événement de même instant validé après le premier
    passage, sans rendre le déjà vu."""
    first = await add_write(env, hours(3), title="Premier")
    seen = (await _page(env)).items
    assert [item.id for item in seen] == [f"memory:{first}:create"]
    late = await add_write(env, hours(3), title="Arrivé après")
    cursor = seen[0]
    again = await _page(env, after=cursor.at, after_id=cursor.id)
    # À instant égal, « plus récent » = un `id` plus grand que celui du curseur.
    late_id = f"memory:{late}:create"
    assert [item.id for item in again.items] == ([late_id] if late_id > cursor.id else [])
    assert (await _page(env, after=cursor.at)).items == []  # sans `after_id` : strictement après
    past = await _page(env, after=cursor.at, after_id="")  # curseur le plus bas : tout l'instant
    assert {item.id for item in past.items} == {f"memory:{first}:create", late_id}


async def test_tie_beyond_the_source_limit_is_not_lost(env: Env) -> None:
    """Plus d'ex æquo écartés que `limit` : la source est redemandée plus large, rien ne manque."""
    ids = [await add_write(env, hours(3), title=f"Ex æquo {n}") for n in range(6)]
    top = sorted((f"memory:{i}:create" for i in ids), reverse=True)
    first = await _page(env, limit=3)
    assert [item.id for item in first.items] == top[:3]
    nxt = await _page(env, before=first.items[-1].at, before_id=top[2], limit=3)
    assert [item.id for item in nxt.items] == top[3:]


async def test_failing_source_is_skipped(
    env: Env, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Une source qui lève (même une erreur SQL) ne fait pas tomber le fil : les autres rendent
    leurs événements ; le journal ne porte que le nom de la source et la classe de l'exception."""
    caplog.set_level(logging.DEBUG, logger="app")
    await add_brief(env, hours(1))

    async def broken(db: AsyncSession, *args: object) -> list[object]:
        raise RuntimeError("Donnée secrète : Société Fictive")

    async def broken_sql(db: AsyncSession, *args: object) -> list[object]:
        await db.execute(text("select * from table_inexistante"))
        return []

    monkeypatch.setattr(feed, "ACTIVITY_SOURCES", (broken, broken_sql, *feed.ACTIVITY_SOURCES))
    page = await _page(env)
    assert [item.kind for item in page.items] == ["brief"]
    log = "\n".join(record.getMessage() for record in caplog.records)
    assert "broken" in log and "RuntimeError" in log and "OperationalError" in log
    assert "secrète" not in log and "Société" not in log and "table_inexistante" not in log


async def test_january_own_capture_is_not_activity(env: Env) -> None:
    """Sa capture rapide (écrite par l'Archiviste à sa demande) n'est pas un travail de fond ;
    un autre écrit de l'Archiviste, lui, en est un."""
    await add_write(env, hours(1), author=CAPTURE_AUTHOR, reason=CAPTURE_REASON, title="Capture")
    await add_write(
        env, hours(2), author=CAPTURE_AUTHOR, reason=reflect_reason("Pandas"), title="Acquis"
    )
    kept = await add_write(env, hours(3), author=CAPTURE_AUTHOR, reason="Le document dit X.")
    no_reason = await add_write(env, hours(4), author=CAPTURE_AUTHOR, reason=None)
    other = await add_write(env, hours(5), author="scribe", reason=CAPTURE_REASON)
    page = await _page(env)
    assert [item.id for item in page.items] == [
        f"memory:{other}:create",
        f"memory:{no_reason}:create",
        f"memory:{kept}:create",
    ]
