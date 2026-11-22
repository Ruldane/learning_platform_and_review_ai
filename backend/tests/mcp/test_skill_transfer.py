"""Lecture et programmation par délégation, avec annulation de la programmation."""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import evidence
from app.features.skills.service import SkillsService
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.mcp.test_direct_write import undo_last


async def test_mcp_can_read_and_schedule_but_cannot_prepare_or_answer(
    app: FastAPI, claude: Mcp, db_session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    skills = SkillsService(db_session, app.state.local_user_id)
    await skills.raise_levels(
        ["Transfert SQL"], "valide", evidence("quiz", "quiz-fictif", "Agrégations", now)
    )
    skill_id = await skills.skill_id_for("Transfert SQL")
    await db_session.commit()

    reader = await claude.token(("skill_transfer",), "read")
    writer = await claude.token(("skill_transfer",), "write")
    readable = (await claude.rpc(reader, "tools/list")).json()["result"]["tools"]
    writable = (await claude.rpc(writer, "tools/list")).json()["result"]["tools"]
    assert "skill_transfer_schedule" not in {tool["name"] for tool in readable}
    assert {tool["name"] for tool in writable if tool["name"].startswith("skill_transfer_")} == {
        "skill_transfer_list_proofs",
        "skill_transfer_list",
        "skill_transfer_read",
        "skill_transfer_schedule",
    }
    result, failed = await call(
        claude, reader, "skill_transfer_list_proofs", {"skill_id": skill_id}
    )
    assert not failed, result
    [proof] = result["data"]
    result, failed = await call(
        claude,
        writer,
        "skill_transfer_schedule",
        {
            "skill_id": skill_id,
            "proof_id": proof["id"],
            "due_on": (now.date() + timedelta(days=2)).isoformat(),
        },
    )
    assert not failed, result
    transfer_id = result["data"]["id"]
    assert "answer" not in result["data"]
    path = f"{API}/skill-transfers/{transfer_id}"
    assert (await claude.http.get(path)).status_code == 200
    undone = await undo_last(claude)
    assert undone.status_code == 200, undone.text
    assert (await claude.http.get(path)).status_code == 404
