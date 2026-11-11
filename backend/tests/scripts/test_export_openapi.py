import json
from pathlib import Path

from scripts.export_openapi import build_app, main, render_openapi


def test_check_detects_stale_file(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    out.write_text("{}")
    assert main(["--check", "--out", str(out)]) == 1
    assert main(["--out", str(out)]) == 0
    assert main(["--check", "--out", str(out)]) == 0


def test_check_fails_when_file_is_missing(tmp_path: Path) -> None:
    assert main(["--check", "--out", str(tmp_path / "absent.json")]) == 1


def test_export_is_sorted_indented_and_deterministic() -> None:
    text = render_openapi(build_app())
    assert text == render_openapi(build_app())
    assert text.endswith("}\n")
    assert "\n  " in text
    spec = json.loads(text)
    assert list(spec) == sorted(spec)
    assert "/api/v1/health" in spec["paths"]


def test_check_does_not_write(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    out.write_text("{}")
    main(["--check", "--out", str(out)])
    assert out.read_text() == "{}"
