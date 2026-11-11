"""Exporte le contrat OpenAPI du back dans `contracts/openapi.json`.

Usage, depuis backend/ :
    python -m scripts.export_openapi [--check] [--out ../contracts/openapi.json]
Avec `--check`, rien n'est écrit : le code de sortie est 1 si le fichier diffère.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI

from app.config import Settings
from app.main import create_app

DEFAULT_OUT = Path(__file__).resolve().parent.parent.parent / "contracts" / "openapi.json"


def build_app() -> FastAPI:
    """Construit l'application sans lire `.env` ni toucher à la base (pas de lifespan)."""
    return create_app(Settings(_env_file=None, data_dir=Path("data-unused")))


def render_openapi(app: FastAPI) -> str:
    """JSON trié et indenté, terminé par un saut de ligne, pour des diffs lisibles."""
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_openapi(app: FastAPI, out: Path) -> str:
    """Écrit le contrat dans `out` (UTF-8, fins de ligne LF) et renvoie son texte."""
    text = render_openapi(app)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text.encode("utf-8"))
    return text


def _is_up_to_date(text: str, out: Path) -> bool:
    return out.is_file() and out.read_text(encoding="utf-8") == text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporte le contrat OpenAPI.")
    parser.add_argument("--check", action="store_true", help="échoue si le fichier diffère")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    app = build_app()
    if args.check:
        if _is_up_to_date(render_openapi(app), args.out):
            return 0
        print(
            f"{args.out} est périmé : relance `python -m scripts.export_openapi` dans backend/.",
            file=sys.stderr,
        )
        return 1
    export_openapi(app, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
