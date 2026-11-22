"""Serveur local et stockage jetable du parcours portfolio."""

import argparse
from pathlib import Path

import uvicorn

from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    settings.portfolio_public_origin = f"http://localhost:{args.port}"
    migrate(settings)
    uvicorn.run(build_app(settings), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
