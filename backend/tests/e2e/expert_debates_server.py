"""Serveur jetable du débat sourcé, sur les mêmes doubles que les tests API."""

import argparse
from pathlib import Path

import uvicorn

from app.providers.search.fake import FakeSearch
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.support.expert_debates import expert_scripts, script_expert_sources
from tests.support.memory import FakeWebReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin)
    migrate(settings)
    app = build_app(settings, scripts=expert_scripts())
    providers = app.state.injected_research_providers
    assert isinstance(providers.web, FakeWebReader) and isinstance(providers.searxng, FakeSearch)
    script_expert_sources(providers.web, providers.searxng)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
