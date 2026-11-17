"""Tests d'évasion ajoutés par la relecture de 10.A1 : objets System V rendus à un autre
propriétaire (I1) et noms de processus piégés (I2). Contre le vrai conteneur, comme
`test_escape.py`."""

import pytest

from tests.sandbox_live import programs_review as R
from tests.sandbox_live.conftest import Bac

pytestmark = pytest.mark.sandbox_live


async def test_sysv_object_with_changed_owner_is_removed(bac: Bac) -> None:
    first = (await bac.run(R.SYSV_GIVE_AWAY)).json()
    assert all(made >= 0 for made in first["made"].values()), first
    assert first["given"] == {"shm": [0, 0], "msg": [0, 0], "sem": [0, 0]}, first  # IPC_SET permis
    tables = (await bac.run(R.SYSV_TABLES)).json()
    assert tables == {"shm": [], "sem": [], "msg": []}, tables  # quel que soit `uid` ou `cuid`
    await bac.hello()


async def test_process_name_cannot_break_the_sweep(bac: Bac) -> None:
    run = await bac.run(R.RENAMED_PROCESSES, timeout_s=3)
    assert run.result.status in {"timeout", "killed"}
    assert await bac.sandbox.healthy()  # le lanceur n'est pas tombé
    await bac.hello()
    from tests.sandbox_live import programs_abuse as A  # noqa: PLC0415

    assert (await bac.run(A.INSPECT_AFTER)).json()["procs"] == []
