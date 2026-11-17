"""Contrôle de la phase 8 : l'étape `journaux` (rien de personnel dans les journaux du back), la
partie inconnue et la ligne de commande (codes de sortie, journaux lus sur l'entrée standard)."""

import io
from typing import Any

import httpx
import pytest

import scripts.check_phase8 as check
from scripts.check_phase8 import BRIEF_STEPS, CheckFailed, run_check
from tests.scripts.phase8_support import NOON, SENTENCES, FakeApi, fails, play


@pytest.fixture(autouse=True)
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.phase8_common.POLL_S", 0.0)
    monkeypatch.setattr("scripts.phase8_plan.local_now", lambda zone: NOON)


# -- journaux ---------------------------------------------------------------------------------


async def test_logs_step_fails_without_logs() -> None:
    await fails(FakeApi(), "brief", "journaux", "non fournis", logs=None)


@pytest.mark.parametrize("part", ["brief", "journaux"])
@pytest.mark.parametrize("empty", ["", "\n", "  \n \t\n"])
async def test_logs_step_fails_on_empty_logs(part: str, empty: str) -> None:
    """Une entrée vide (début mal formé, tube cassé, mauvais service) n'est jamais un succès."""
    await fails(FakeApi(), part, "journaux", "vides", logs=empty)


@pytest.mark.parametrize(
    ("part", "leak", "secret"),
    [
        ("radar", "relevé du poste Développeur Python lancé", "Développeur"),
        ("radar", "zone Lyon", "Lyon"),
        ("radar", "lien https://jobs.example/offre-b lu", "offre-b"),
        ("radar", "entreprise Maison C", "Maison"),
        ("brief", "ressource https://docs.example/guide", "docs.example"),
        ("brief", "titre Un guide", "guide"),
        ("brief", SENTENCES[0], "rythme"),
    ],
)
async def test_logs_step_fails_on_forbidden_data_without_copying_it(
    part: str, leak: str, secret: str
) -> None:
    with pytest.raises(CheckFailed) as failed:
        await play(FakeApi(), part, logs=f"INFO ligne\nINFO {leak}\n")

    assert failed.value.step == "journaux" and "Donnée personnelle" in str(failed.value)
    assert secret not in str(failed.value)


async def test_logs_step_counts_clean_lines(capsys: pytest.CaptureFixture[str]) -> None:
    await play(FakeApi(), "brief", logs="INFO brief b1 créé\nINFO conseil 2 phrases\n")

    assert "2 ligne(s) relue(s), sans donnée" in capsys.readouterr().out


async def test_journaux_part_alone_plays_only_the_logs_step(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--part journaux` : aucune requête à l'API, les journaux d'après l'essai, mêmes motifs."""
    fake = FakeApi()
    steps = await play(fake, "journaux", logs="INFO relevé 3 fini\nINFO brief b1 créé\n")

    assert steps == ["journaux"] and not fake.seen and not fake.puts
    out = capsys.readouterr().out
    assert "2 ligne(s) relue(s), motifs génériques seulement" in out
    assert "sans donnée" not in out
    await fails(FakeApi(), "journaux", "journaux", "non fournis", logs=None)
    await fails(FakeApi(), "journaux", "journaux", "Donnée personnelle", logs="INFO zone Lyon\n")


async def test_unknown_part_is_refused() -> None:
    async with httpx.AsyncClient(base_url="http://api") as client:
        with pytest.raises(CheckFailed) as refused:
            await run_check(client, part="autre", timeout_s=10)  # type: ignore[arg-type]
    assert refused.value.step == "partie"


# -- ligne de commande ------------------------------------------------------------------------


def _fake_run(monkeypatch: pytest.MonkeyPatch, outcome: Exception | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        calls.append(kwargs)
        if outcome is not None:
            raise outcome
        return list(BRIEF_STEPS)

    monkeypatch.setattr(check, "run_check", fake)
    return calls


def test_main_exits_with_one_on_a_failed_step(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_run(monkeypatch, CheckFailed("conseil", "Conseil « failed »."))

    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "brief"])

    assert exited.value.code == 1
    assert "[échec] conseil : Conseil « failed »." in capsys.readouterr().err


def test_main_exits_with_zero_and_reads_the_logs_from_the_standard_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _fake_run(monkeypatch, None)
    monkeypatch.setattr("sys.stdin", io.StringIO("depuis l'entrée standard"))

    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "radar", "--logs-file", "-"])

    assert exited.value.code == 0
    assert calls[0]["part"] == "radar" and calls[0]["logs"] == "depuis l'entrée standard"
    assert "réussi : 5 étapes (radar)" in capsys.readouterr().out


def test_journaux_part_alone_reads_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """La ligne de commande : `--part journaux --logs-file -` lit l'entrée standard (les journaux
    passés **après** l'essai) sans joindre l'API ; l'aide le dit."""
    monkeypatch.setattr("sys.stdin", io.StringIO("INFO brief b1 créé\nINFO conseil 2 phrases\n"))
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1", "--part", "journaux", "--logs-file", "-"])
    assert exited.value.code == 0
    out = capsys.readouterr().out
    assert "motifs génériques seulement" in out and "réussi : 1 étapes (journaux)" in out

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    with pytest.raises(SystemExit) as empty:
        check.main(["--api", "http://localhost:1", "--part", "journaux", "--logs-file", "-"])
    assert empty.value.code == 1 and "vides" in capsys.readouterr().err

    monkeypatch.setattr("sys.stdin", io.StringIO("INFO zone Lyon\n"))
    with pytest.raises(SystemExit) as leaked:
        check.main(["--api", "http://localhost:1", "--part", "journaux", "--logs-file", "-"])
    assert leaked.value.code == 1
    assert "Lyon" not in capsys.readouterr().err

    assert "APRÈS l'essai" in (check.__doc__ or "")
    assert "APRÈS l'essai" in check.build_parser().format_help()


def test_main_defaults_to_planifie_without_logs_and_refuses_an_unknown_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_run(monkeypatch, None)
    with pytest.raises(SystemExit):
        check.main(["--api", "http://localhost:1"])
    assert calls[0]["logs"] is None and calls[0]["part"] == "planifie"

    with pytest.raises(SystemExit) as refused:
        check.main(["--part", "autre"])
    assert refused.value.code == 2
