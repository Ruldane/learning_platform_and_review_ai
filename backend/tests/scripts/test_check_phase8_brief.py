"""Contrôle de la phase 8, partie `brief`, contre une fausse API (`phase8_support`) : les
rubriques, le conseil (prêt, en attente, définitif), la ressource, la relecture. Aucun réseau ni
LLM, rien d'affiché qui soit une phrase du conseil ou un lien."""

from typing import Any

import pytest

from scripts.check_phase8 import BRIEF_STEPS, CheckFailed
from scripts.phase4_steps import Run
from scripts.phase8_brief import check_reread
from scripts.phase8_common import Track
from tests.scripts.phase8_support import (
    NOON,
    SENTENCES,
    FakeApi,
    brief_json,
    fails,
    no_events,
    play,
)


@pytest.fixture(autouse=True)
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.phase8_common.POLL_S", 0.0)
    monkeypatch.setattr("scripts.phase8_plan.local_now", lambda zone: NOON)


# -- brief ------------------------------------------------------------------------------------


async def test_brief_part_checks_sections_advice_resource_and_reread(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeApi()
    fake.pending_gets = 2

    done = await play(fake, "brief")

    assert done == list(BRIEF_STEPS)
    out = capsys.readouterr().out
    assert "brief b1 (origine opening) : 12 fiche(s), 2 relance(s) due(s), 1 offre(s)" in out
    assert "conseil prêt en" in out and "2 phrases, 2 nombre(s) cité(s)" in out
    assert "3 appel(s) LLM ; 0.0123 $" in out and "ressource lue sur docs.example" in out
    for secret in (*SENTENCES, "Un guide", "docs.example/guide"):
        assert secret not in out


async def test_brief_part_accepts_no_resource_and_says_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeApi()
    fake.brief_over = {"resource": None}

    await play(fake, "brief")

    assert "aucune ressource (null)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("over", "step", "message"),
    [
        (
            {"advice_status": "unavailable", "advice": None},
            "conseil",
            "« unavailable » : définitif",
        ),
        ({"advice_status": "failed", "advice": None}, "conseil", "« failed » : définitif"),
        ({"advice": ["Une seule."]}, "conseil", "1 phrase(s) de conseil, 2 attendues"),
        ({"advice": ["Tu as 99 fiches.", "Courage."]}, "conseil", "1 nombre(s) du conseil absent"),
        ({"reviews": None}, "rubriques", "attendues rangées"),
        ({"offers": {"run_id": None, "items": [{"score": 50}]}}, "rubriques", "score sous 70"),
        (
            {"resource": {**brief_json()["resource"], "domain": "autre.example"}},
            "ressource",
            "site",
        ),
        ({"resource": {**brief_json()["resource"], "why": " "}}, "ressource", "manquant"),
    ],
    ids=[
        "indisponible",
        "échec",
        "une phrase",
        "nombre inconnu",
        "rubrique",
        "score",
        "site",
        "raison",
    ],
)
async def test_brief_part_fails_with_a_readable_message(
    over: dict[str, Any], step: str, message: str
) -> None:
    fake = FakeApi()
    fake.brief_over = over

    await fails(fake, "brief", step, message)


async def test_brief_part_fails_when_the_advice_stays_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.phase8_brief.ADVICE_S", -1.0)
    fake = FakeApi()
    fake.pending_gets = 99

    await fails(fake, "brief", "conseil", "conseil toujours en attente")


async def test_reread_fails_when_the_second_get_is_another_brief() -> None:
    fake = FakeApi()
    fake.brief_over = {"id": "b2"}

    async with fake.client() as client:
        with pytest.raises(CheckFailed) as failed:
            await check_reread(Run(client, no_events, 5.0), Track(brief=brief_json(id="b1")))

    assert failed.value.step == "relecture" and "b2" in str(failed.value)


async def test_reread_fails_when_the_second_get_changes_the_advice() -> None:
    fake = FakeApi()
    fake.brief_over = {"advice": ["Autre phrase.", "Encore une."]}

    async with fake.client() as client:
        with pytest.raises(CheckFailed, match="« advice » a changé"):
            await check_reread(Run(client, no_events, 5.0), Track(brief=brief_json()))
