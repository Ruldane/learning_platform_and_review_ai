"""Étapes du contrôle de la phase 7 hors du parcours complet : les préalables manquants, la fiche
montrée par l'Assistant de suivi (champs justes, rien d'inventé), l'entreprise de la phrase qui
change à chaque passage, les appels du modèle comptés par événement, et la ligne de commande
(codes de sortie, lecture des journaux). Aucun réseau ni LLM."""

import io
from typing import Any

import httpx
import pytest

import scripts.check_phase7 as check
from scripts.check_phase7 import KIT_STEPS, SUIVI_STEPS, CheckFailed
from scripts.phase4_steps import Run
from scripts.phase6_rules import plain
from scripts.phase7_common import Track, count_calls
from scripts.phase7_fiche import load_prerequisites
from scripts.phase7_intake import (
    NAMES,
    POSITION,
    PREFIX,
    check_question,
    fresh_company,
    sentence_of,
)

YESTERDAY = "2026-11-14"


def question(**over: str) -> dict[str, Any]:
    values = {
        "company": f"{PREFIX} Cèdre",
        "title": POSITION,
        "status": "applied",
        "applied_on": YESTERDAY,
        "channel": "linkedin",
        "contact_name": "",
        "contact_role": "",
        "notes": "",
    } | over
    return {
        "question": "Create this application?",
        "options": [{"value": "create"}, {"value": "cancel"}],
        "fields": [{"id": name, "value": value} for name, value in values.items()],
    }


def test_the_shown_fiche_must_carry_the_right_fields() -> None:
    check_question("une phrase", question(), f"{PREFIX} Cèdre", YESTERDAY)
    # Accents et casse ne comptent pas (comme la vérification des mots de la phrase).
    check_question("une phrase", question(company=f"{PREFIX} CEDRE"), f"{PREFIX} Cèdre", YESTERDAY)

    wrong = {
        "company": question(company="Autre Société"),
        "title": question(title="Développeuse"),
        "status": question(status="to_apply"),
        "applied_on": question(applied_on="2026-11-15"),
        "channel": question(channel=""),
        "contact_name": question(contact_name="Alex Inventé"),
    }
    for name, shown in wrong.items():
        with pytest.raises(CheckFailed) as failed:
            check_question("une phrase", shown, f"{PREFIX} Cèdre", YESTERDAY)
        assert name in str(failed.value)
        assert "Alex Inventé" not in str(failed.value) and "Autre Société" not in str(failed.value)


def test_the_shown_question_has_no_alert_and_two_options() -> None:
    alert = question()
    alert["options"] = [{"value": "distinct"}, {"value": "open"}, {"value": "cancel"}]
    with pytest.raises(CheckFailed, match="options inattendues"):
        check_question("une phrase", alert, f"{PREFIX} Cèdre", YESTERDAY)
    asked = question()
    asked["question"] = "Create this application? You already have an application."
    with pytest.raises(CheckFailed, match="options inattendues"):
        check_question("une phrase", asked, f"{PREFIX} Cèdre", YESTERDAY)


def test_the_company_of_the_sentence_is_the_first_one_no_fiche_carries() -> None:
    def taken(names: tuple[str, ...]) -> set[str]:
        return {plain(f"{PREFIX} {name}") for name in names}

    assert fresh_company(set()) == f"{PREFIX} {NAMES[0]}"
    assert fresh_company(taken(NAMES[:3])) == f"{PREFIX} {NAMES[3]}"
    with pytest.raises(CheckFailed, match="toutes déjà prises"):
        fresh_company(taken(NAMES))
    sentence = sentence_of(f"{PREFIX} Cèdre")
    assert sentence.startswith("j'ai postulé hier sur LinkedIn chez ")
    assert sentence.endswith(f"pour le poste {POSITION}")


def test_llm_calls_are_the_cost_events_of_the_session() -> None:
    events = [{"type": "cost.updated"}, {"type": "agent.message"}, {"type": "cost.updated"}]

    assert count_calls(events) == 2
    assert count_calls([]) == 0


def _run(handler: Any) -> Run:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://api")

    async def no_events(session_id: str) -> list[dict[str, Any]]:
        raise AssertionError("aucun événement attendu")

    return Run(client, no_events, 30)


def _api(routes: dict[str, Any]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=routes[request.url.path.removeprefix("/api/v1")])

    return handler


@pytest.mark.parametrize(
    ("routes", "message"),
    [
        ({"/profile": {"validated": None}}, "Aucun profil maître validé"),
        ({"/profile": {"validated": {"data": {}}}, "/postings": []}, "Aucune offre fictive"),
        (
            {
                "/profile": {"validated": {"data": {}}},
                "/postings": [{"id": "p1", "status": "ready", "title": "AI Product Engineer"}],
                "/cv/versions": [{"id": "v1", "status": "failed", "number": 1}],
            },
            "Aucune version de CV prête",
        ),
    ],
    ids=["profil", "offre", "version"],
)
async def test_missing_prerequisites_say_to_run_phase_6(
    routes: dict[str, Any], message: str
) -> None:
    run = _run(_api(routes))

    with pytest.raises(CheckFailed) as failed:
        await load_prerequisites(run, Track(), "fiche depuis offre")

    assert message in str(failed.value) and "phase 6" in str(failed.value)
    await run.client.aclose()


async def test_an_unreachable_api_is_a_french_failure_without_details() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret interne")

    run = _run(down)

    with pytest.raises(CheckFailed) as failed:
        await load_prerequisites(run, Track(), "fiche depuis offre")

    assert "API injoignable (ConnectError)" in str(failed.value)
    assert "secret" not in str(failed.value)
    await run.client.aclose()


def test_the_parts_list_their_steps() -> None:
    assert check.STEPS_BY_PART == {"suivi": SUIVI_STEPS, "kit": KIT_STEPS}
    assert SUIVI_STEPS == (
        "fiche depuis offre",
        "doublon",
        "une phrase",
        "relance",
        "indicateurs",
        "journaux",
    )
    assert KIT_STEPS == ("fiche depuis offre", "kit", "journaux")


def _fake_run(monkeypatch: pytest.MonkeyPatch, outcome: Exception | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        calls.append(kwargs)
        if outcome is not None:
            raise outcome
        return list(KIT_STEPS)

    monkeypatch.setattr(check, "run_check", fake)
    return calls


def test_main_exits_with_one_on_a_failed_step(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_run(monkeypatch, CheckFailed("kit", "Pièce letter : 200 mot(s)."))

    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "kit"])

    assert exited.value.code == 1
    assert "[échec] kit : Pièce letter : 200 mot(s)." in capsys.readouterr().err


def test_main_exits_with_zero_and_reads_the_logs_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _fake_run(monkeypatch, None)
    logs = tmp_path / "back.log"
    logs.write_text("ligne\nautre ligne\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "kit", "--logs-file", str(logs)])

    assert exited.value.code == 0
    assert calls[0]["part"] == "kit" and calls[0]["logs"] == "ligne\nautre ligne\n"
    assert "réussi : 3 étapes (kit)" in capsys.readouterr().out


def test_main_reads_the_logs_from_standard_input(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_run(monkeypatch, None)
    monkeypatch.setattr("sys.stdin", io.StringIO("depuis l'entrée standard"))

    with pytest.raises(SystemExit):
        check.main(["--api", "http://localhost:1", "--logs-file", "-"])

    assert calls[0]["logs"] == "depuis l'entrée standard" and calls[0]["part"] == "suivi"


def test_main_without_logs_file_passes_none_and_refuses_an_unknown_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_run(monkeypatch, None)
    with pytest.raises(SystemExit):
        check.main(["--api", "http://localhost:1"])
    assert calls[0]["logs"] is None

    with pytest.raises(SystemExit) as refused:
        check.main(["--part", "tout"])
    assert refused.value.code == 2
