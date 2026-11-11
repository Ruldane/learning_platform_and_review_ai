from collections.abc import Iterator

import pytest

from tests.agents.graphs_for_tests import Probe
from tests.sessions_support import use_test_runtime


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> Iterator[Probe]:
    """Avant l'app (autouse) : son lifespan construit le runtime avec les parcours de test."""
    probe = use_test_runtime(monkeypatch)
    yield probe
    probe.release_b.set()
