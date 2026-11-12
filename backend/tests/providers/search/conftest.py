import pytest

from app.core.logging import configure_logging


@pytest.fixture(autouse=True)
def production_logging() -> None:
    """Journaux réglés comme en production (httpx en WARNING) : `caplog` voit alors exactement
    ce qu'un fournisseur de recherche écrirait."""
    configure_logging("INFO", lambda: [])
