"""Délais des relances (7.1) : la règle vit dans `settings`, les candidatures l'importent."""

import subprocess
import sys
from pathlib import Path

from app.features.applications.service import schedule
from app.features.settings import delays, service

BACKEND_DIR = Path(__file__).resolve().parents[3]


def test_delays_are_shared_through_the_settings_service() -> None:
    assert service.validated_delays is delays.validated_delays
    assert schedule.validated_delays is delays.validated_delays
    assert schedule.DEFAULT_DELAYS == delays.DEFAULT_DELAYS == (7, 14, 21)


def test_settings_never_import_applications() -> None:
    """Un seul sens : `applications` importe `settings.service`, jamais l'inverse (pas de cycle)."""
    code = (
        "import sys, app.features.settings.schemas, app.features.settings.service;"
        "sys.exit(any(m.startswith('app.features.applications') for m in sys.modules))"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, check=False)
    assert done.returncode == 0
