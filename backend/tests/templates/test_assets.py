"""Fichiers figés des PDF (D89) : Mermaid à empreinte vérifiée, même majeure que le front."""

import hashlib
import json
from pathlib import Path

import pytest

from app.templates import assets
from app.templates.assets import MERMAID_SHA256, MERMAID_VERSION, asset, template_file

FRONT_PACKAGE = Path(__file__).resolve().parents[3] / "frontend" / "package.json"


def test_mermaid_asset_matches_pinned_hash() -> None:
    assert hashlib.sha256(asset("mermaid.min.js")).hexdigest() == MERMAID_SHA256


def test_mermaid_version_follows_the_front_major() -> None:
    if not FRONT_PACKAGE.exists():
        pytest.skip("front absent (image du back)")
    wanted = json.loads(FRONT_PACKAGE.read_text(encoding="utf-8"))["dependencies"]["mermaid"]
    assert wanted.lstrip("^~").split(".")[0] == MERMAID_VERSION.split(".")[0]


def test_tampered_mermaid_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "mermaid.min.js").write_bytes(b"window.evil = true")
    monkeypatch.setattr(assets, "_ASSETS_DIR", tmp_path)
    asset.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            asset("mermaid.min.js")
    finally:
        asset.cache_clear()


@pytest.mark.parametrize("name", ["../__init__.py", "a/b.js", "", ".hidden", "..", "X.js"])
def test_asset_names_are_simple(name: str) -> None:
    with pytest.raises(ValueError):
        asset(name)


@pytest.mark.parametrize("path", ["lesson/../assets.py", "other/x.css", "lesson/", "/etc/passwd"])
def test_template_paths_are_bounded(path: str) -> None:
    with pytest.raises(ValueError):
        template_file(path)


def test_render_js_is_strict_and_signals_ready() -> None:
    script = asset("render.js").decode()
    assert 'securityLevel: "strict"' in script and "startOnLoad: false" in script
    assert "window.__lessonReady = true" in script
    for forbidden in ("fetch(", "XMLHttpRequest", "eval(", "import(", "http"):
        assert forbidden not in script, forbidden


def test_footer_has_page_numbers_and_no_script() -> None:
    footer = template_file("lesson/footer.html")
    assert 'class="pageNumber"' in footer and 'class="totalPages"' in footer
    assert "<script" not in footer and "http" not in footer
