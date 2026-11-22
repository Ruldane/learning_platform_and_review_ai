import pytest

from tests.sessions_support import use_test_runtime


@pytest.fixture
def scripted_professor(monkeypatch: pytest.MonkeyPatch) -> None:
    use_test_runtime(monkeypatch, ["Voici l'explication [1]. Référence inconnue [42]."])
