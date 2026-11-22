from app.features.radar.service.role_offers import OfferSkill
from app.features.skill_market.metrics import coverage, demand


def test_demand_counts_each_offer_once_and_keeps_empty_samples_explicit() -> None:
    offers = (
        (OfferSkill("Python", True), OfferSkill("python", False)),
        (OfferSkill("SQL", True),),
        (OfferSkill("PYTHON", False),),
    )

    assert demand(offers, "python") == 66.7
    assert demand(offers, "Docker") == 0.0
    assert demand((), "Python") is None


def test_learning_one_skill_increases_covered_requirements_only_when_sufficient() -> None:
    offers = (
        (OfferSkill("Python", True), OfferSkill("SQL", True)),
        (OfferSkill("Python", True), OfferSkill("Docker", True)),
        (OfferSkill("SQL", True),),
        (),
    )

    assert coverage(offers, {"sql"}) == 1
    assert coverage(offers, {"sql", "python"}) == 2
