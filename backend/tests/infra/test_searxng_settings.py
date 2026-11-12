from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "infra/searxng/settings.yml"
REQUIRED_ENGINES = {"wikipedia", "github", "arxiv", "stackoverflow", "youtube"}


def _load() -> dict[str, object]:
    loaded = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_searxng_has_json_and_required_engines() -> None:
    cfg = _load()
    assert "json" in cfg["search"]["formats"]  # type: ignore[index]
    enabled = {
        e["name"]
        for e in cfg.get("engines", [])  # type: ignore[attr-defined]
        if not e.get("disabled", False)
    }
    assert enabled >= REQUIRED_ENGINES
    assert cfg["server"]["limiter"] is False  # type: ignore[index]


def test_searxng_extends_the_default_settings() -> None:
    assert _load()["use_default_settings"] is True


def test_searxng_secret_is_not_in_the_file() -> None:
    # La clé vient de SEARXNG_SECRET (compose) ; le fichier ne doit pas en porter une.
    assert "secret_key" not in _load().get("server", {})  # type: ignore[operator]


# Moteurs généralistes du `settings.yml` par défaut de l'image figée (2026.11.9-57ff753ad) ;
# `startpage` et `mojeek` y sont `inactive: true` (non chargés) : il faut les réactiver.
GENERAL_ENGINES = {"duckduckgo", "brave", "mojeek", "startpage", "qwant", "bing", "google"}
INACTIVE_BY_DEFAULT = {"mojeek", "startpage"}


def test_searxng_has_three_general_engines_and_json() -> None:
    cfg = _load()
    assert "json" in cfg["search"]["formats"]  # type: ignore[index]
    active = set()
    for engine in cfg.get("engines", []):  # type: ignore[attr-defined]
        name = engine["name"]
        if engine.get("disabled", False):
            continue
        if name in INACTIVE_BY_DEFAULT and engine.get("inactive", True):
            continue
        active.add(name)
    assert len(active & GENERAL_ENGINES) >= 3
