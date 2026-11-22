"""Routine locale, faux fournisseurs et échéance du lendemain en recette."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn

import app.main as composition
from app.features.routines.service import run_daily
from app.features.settings.service import scheduled_users
from app.scheduler.base import JobContext, JobSpec
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir


async def tomorrow(ctx: JobContext) -> None:
    async with ctx.session_factory() as db:
        owners = await scheduled_users(db)
    now = (datetime.now(UTC) + timedelta(days=1)).replace(hour=20)
    for owner in owners:
        async with ctx.session_factory() as db:
            await run_daily(db, owner, now)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8901)
    parser.add_argument("--origin", default="http://127.0.0.1:5301")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    settings.scheduler_enabled = True
    composition.JOBS[:] = [JobSpec("routines", timedelta(seconds=1), tomorrow)]
    migrate(settings)
    uvicorn.run(build_app(settings), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
