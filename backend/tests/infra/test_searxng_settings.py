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
