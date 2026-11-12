import pytest

from app.features.program.service.budget import Budget


@pytest.fixture
def budget() -> Budget:
    return Budget(weekday_minutes=120, weekend_minutes=240)  # 840 par semaine, plafond 714
