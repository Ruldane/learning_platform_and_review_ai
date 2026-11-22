import pytest

from app.features.radar.service.salary_sample import annual_euro_range


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("50 à 65 k€ bruts par an", (50000, 65000)),
        ("50,5 k€ – 72 k€ bruts/an", (50500, 72000)),
        ("70,000 EUR gross per year", (70000, 70000)),
        ("50 € à 70 k€ bruts par an", (50, 70000)),
        ("55 000 à 70 000 € brut annuel", (55000, 70000)),
        ("55 000 € brut annuel + 5 %", None),
        ("70 k€", None),
        ("5 000 € net par mois", None),
        ("50 kCHF brut annuel", None),
        ("−50 k€ brut annuel", None),
        ("jusqu’à 70 k€ brut annuel", None),
    ],
)
def test_only_unambiguous_annual_euro_amounts(
    source: str, expected: tuple[int, int] | None
) -> None:
    assert annual_euro_range(source) == expected
