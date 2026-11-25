"""The hidden cases speak the English challenge and still serve files started in French."""

import json

from app.features.boss.service import diagnostic


def test_cases_carry_the_english_and_the_french_flag() -> None:
    rows = [row for case in json.loads(diagnostic._DATA) for row in case]
    assert rows and all(row["urgent"] == row["urgente"] for row in rows)


def test_worker_prefers_schedule_and_falls_back_to_planifier() -> None:
    compile(diagnostic._WORKER, "worker.py", "exec")
    assert 'getattr(service, "schedule", None) or service.planifier' in diagnostic._WORKER
