import time

import pytest
from youtube_transcript_api import (
    FetchedTranscript,
    FetchedTranscriptSnippet,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from app.providers.web.base import UrlForbidden, UrlUnreadable, WebDocument, youtube_video_id
from app.providers.web.youtube import TranscriptApiYoutube
from tests.support.memory import FakeWebReader

VIDEO = "dQw4w9WgXcQ"
WATCH = f"https://www.youtube.com/watch?v={VIDEO}"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=3",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "http://youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
        "https://WWW.YouTube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_video_id_forms(url: str) -> None:
    assert youtube_video_id(url) == "dQw4w9WgXcQ"


def test_video_id_rejects_other_hosts() -> None:
    assert youtube_video_id("https://example.com/watch?v=dQw4w9WgXcQ") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://evil.example/?u=https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=court",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ%2F..",
        "https://www.youtube.com/watch?v=dQw4w9WgXc!",
        "https://user:pw@www.youtube.com/watch?v=dQw4w9WgXcQ",
        "ftp://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/channel/dQw4w9WgXcQ",
        "https://youtu.be/",
        "pas une url",
    ],
)
def test_video_id_rejects_anything_else(url: str) -> None:
    assert youtube_video_id(url) is None


def _transcript(*texts: str) -> FetchedTranscript:
    snippets = [
        FetchedTranscriptSnippet(text=t, start=float(i), duration=1.0) for i, t in enumerate(texts)
    ]
    return FetchedTranscript(
        snippets=snippets,
        video_id=VIDEO,
        language="Français",
        language_code="fr",
        is_generated=False,
    )


def _patch_fetch(
    monkeypatch: pytest.MonkeyPatch, result: object, seen: list[object] | None = None
) -> None:
    def fake(self: YouTubeTranscriptApi, video_id: str, languages: object = ("en",)) -> object:
        if seen is not None:
            seen.append((video_id, tuple(languages)))  # type: ignore[arg-type]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(YouTubeTranscriptApi, "fetch", fake)


def _page(title: str | None, description: str | None) -> WebDocument:
    return WebDocument(WATCH, title, "", None, None, None, description)


async def test_transcript_joined(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    _patch_fetch(monkeypatch, _transcript("a", "b"), seen)
    reader = FakeWebReader({WATCH: _page("Titre", "Desc")})
    got = await TranscriptApiYoutube(reader).transcript(f"https://youtu.be/{VIDEO}")
    assert (got.text, got.from_transcript, got.video_id) == ("a b", True, VIDEO)
    assert got.title == "Titre" and seen == [(VIDEO, ("fr", "en"))]
    assert reader.calls == [(WATCH, False)]


async def test_transcript_whitespace_is_normalised_and_title_is_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fetch(monkeypatch, _transcript("bonjour\n", "  à tous\ndeux"))
    got = await TranscriptApiYoutube(FakeWebReader()).transcript(WATCH)
    assert got.text == "bonjour à tous deux" and got.title is None and got.from_transcript


async def test_fallback_to_title_and_description(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, TranscriptsDisabled(VIDEO))
    reader = FakeWebReader({WATCH: _page("Titre", "Une description.")})
    got = await TranscriptApiYoutube(reader).transcript(f"https://www.youtube.com/shorts/{VIDEO}")
    assert reader.calls == [(WATCH, False)]
    assert (got.title, got.text, got.from_transcript) == (
        "Titre",
        "Titre\n\nUne description.",
        False,
    )


async def test_unexpected_library_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, ConnectionError("réseau"))
    reader = FakeWebReader({WATCH: _page(None, "Seulement la description.")})
    got = await TranscriptApiYoutube(reader).transcript(WATCH)
    assert (got.text, got.from_transcript) == ("Seulement la description.", False)


async def test_slow_transcript_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.web.youtube.TRANSCRIPT_TIMEOUT_S", 0.05)

    def slow(self: YouTubeTranscriptApi, video_id: str, languages: object = ("en",)) -> object:
        time.sleep(0.5)
        return _transcript("trop tard")

    monkeypatch.setattr(YouTubeTranscriptApi, "fetch", slow)
    reader = FakeWebReader({WATCH: _page("Titre", "Desc")})
    assert not (await TranscriptApiYoutube(reader).transcript(WATCH)).from_transcript


@pytest.mark.parametrize(
    "page", [_page(None, None), _page("Titre seul", None), _page("Titre", "   "), UrlForbidden()]
)
async def test_no_transcript_no_description_is_unreadable(
    monkeypatch: pytest.MonkeyPatch, page: object
) -> None:
    _patch_fetch(monkeypatch, TranscriptsDisabled(VIDEO))
    reader = FakeWebReader({WATCH: page})  # type: ignore[dict-item]
    with pytest.raises(UrlUnreadable) as caught:
        await TranscriptApiYoutube(reader).transcript(WATCH)
    assert VIDEO not in caught.value.message


async def test_empty_transcript_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, _transcript("", "  "))
    reader = FakeWebReader({WATCH: _page("Titre", "Desc")})
    assert (await TranscriptApiYoutube(reader).transcript(WATCH)).text == "Titre\n\nDesc"


async def test_not_a_youtube_link_is_refused_without_any_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []
    _patch_fetch(monkeypatch, _transcript("a"), seen)
    reader = FakeWebReader()
    with pytest.raises(UrlUnreadable) as caught:
        await TranscriptApiYoutube(reader).transcript("https://example.com/watch?v=dQw4w9WgXcQ")
    assert caught.value.message == "Lien YouTube non reconnu."
    assert seen == [] and reader.calls == []
