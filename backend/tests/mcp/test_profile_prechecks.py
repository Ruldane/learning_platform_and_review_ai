"""Les contrôles préalables des écritures au profil maître (10.D1) : ils signalent, sans jamais
recopier le contenu ni bloquer (January décide sur la carte « À confirmer »)."""

from typing import Any

from app.features.cv.mcp import modification_precheck, profile_precheck, unsourced_counts
from app.features.projects.mcp import profile_entry_precheck
from app.mcp.base import PrecheckInput


def _request(path: str, body: Any, method: str = "PUT") -> PrecheckInput:
    return PrecheckInput(user_id="u1", method=method, path=path, params={}, body=body)


def _profile(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "identity": {"name": "January"},
        "experiences": [
            {"role": "Dev", "company": "Acme", "sources": ["cv"]},
            {"role": "Lead", "company": "Beta", "sources": ["january"]},
        ],
        "skills": [{"name": "Python", "sources": ["linkedin"]}, {"name": "Go", "sources": []}],
    }
    data.update(overrides)
    return {"data": data, "base_version": 2}


async def test_profile_precheck_counts_facts_without_a_document() -> None:
    verdict = await profile_precheck(_request("/profile", _profile()))
    assert verdict.ok is False
    assert verdict.reasons == (
        "1 expérience(s) sans source de document",
        "1 compétence(s) sans source de document",
    )
    assert "version 2" in (verdict.summary or "")
    assert "Lead" not in str(verdict) and "Go" not in str(verdict)  # jamais le contenu


async def test_profile_precheck_ok_when_every_fact_has_a_document() -> None:
    body = _profile(
        experiences=[{"role": "Dev", "company": "Acme", "sources": ["cv"]}],
        skills=[{"name": "Python", "sources": ["note"]}],
        summary={"text": "Dev Python.", "sources": ["cv"]},
    )
    verdict = await profile_precheck(_request("/profile", body))
    assert verdict.ok is True and verdict.reasons == ()


async def test_profile_precheck_flags_title_and_summary_by_name() -> None:
    body = _profile(title={"text": "Lead", "sources": ["january"]}, experiences=[], skills=[])
    verdict = await profile_precheck(_request("/profile", body))
    assert verdict.reasons == ("1 titre sans source de document",)


async def test_profile_precheck_unreadable_body_does_not_echo_it() -> None:
    verdict = await profile_precheck(_request("/profile", {"data": {"secret": "abc"}}))
    assert verdict.ok is False
    assert "abc" not in str(verdict)


def test_unsourced_counts_ignores_facts_with_a_document() -> None:
    from app.agents.tools.cv_schema import MasterProfileData

    data = MasterProfileData.model_validate(_profile()["data"])
    assert unsourced_counts(data) == {"expérience(s)": 1, "compétence(s)": 1}


async def test_modification_precheck_warns_only_on_confirm() -> None:
    path = "/cv/modifications/m1"
    plain = await modification_precheck(_request(path, {"status": "accepted"}, "PATCH"))
    assert plain.ok is True
    confirm = await modification_precheck(
        _request(path, {"status": "accepted", "confirm": True}, "PATCH")
    )
    assert confirm.ok is False and confirm.reasons
    assert (await modification_precheck(_request(path, None, "PATCH"))).ok is True


async def test_profile_entry_precheck_flags_a_figure_the_description_lacks() -> None:
    path = "/projects/p1/profile-entry"
    ok = await profile_entry_precheck(
        _request(
            path,
            {
                "name": "App",
                "description": "Gain de 30 % de temps.",
                "achievements": ["30 % de gain"],
            },
            "POST",
        )
    )
    assert ok.ok is True
    flagged = await profile_entry_precheck(
        _request(
            path,
            {
                "name": "App",
                "description": "Une appli.",
                "achievements": ["Réduit de 80 % le temps"],
            },
            "POST",
        )
    )
    assert flagged.ok is False
    assert flagged.reasons == (
        "1 chiffre(s) des réalisations absent(s) de la description du projet.",
    )
    assert "80" not in str(flagged)
    bad = await profile_entry_precheck(_request(path, {"description": 3}, "POST"))
    assert bad.ok is False
