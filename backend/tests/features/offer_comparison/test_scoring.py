from app.features.offer_comparison.schemas import OfferComparisonPreferences, OfferComparisonWeights
from app.features.offer_comparison.scoring import OfferFacts, compare


def test_unknown_modes_and_partial_scores_do_not_count_as_zero() -> None:
    first = OfferFacts("a", "Première offre", None, 76, "à déterminer", "Lyon")
    second = OfferFacts("b", "Deuxième offre", None, None, "hybride", "LYON")
    prefs = OfferComparisonPreferences(preferred_work_mode="hybrid", preferred_location="lyon")
    result = compare(first, second, prefs)
    assert result.first.remote == "à déterminer"
    assert result.first.missing == ["work_mode"] and result.second.missing == ["match"]
    assert result.scored_criteria == ["location"]
    assert result.first_score == result.second_score == 100
    assert result.leader == "tie"


def test_zero_weight_can_enter_sensitivity_without_affecting_the_base_result() -> None:
    first = OfferFacts("a", None, None, 75, None, None)
    second = OfferFacts("b", None, None, 25, None, None)
    prefs = OfferComparisonPreferences(
        weights=OfferComparisonWeights(match=0, work_mode=10, location=0)
    )
    result = compare(first, second, prefs)
    assert result.first_score is result.second_score is None
    assert result.leader is None
    assert result.sensitivity[0].higher_weight == 10
    assert result.sensitivity[0].higher_margin == 50
    assert result.sensitivity[0].higher_leader == "first"
