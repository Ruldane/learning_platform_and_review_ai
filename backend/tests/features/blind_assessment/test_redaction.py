from app.agents.tools.cv_schema import CvContent, Identity, MasterProfileData
from app.features.blind_assessment.service.sources import _redactions, anonymized


def test_short_profile_names_also_disappear_from_the_text() -> None:
    one = CvContent(name="Li", headline="Li présente une expérience en organisation")
    two = CvContent(name="Aï", headline="Aï présente le rôle")
    profile = MasterProfileData(identity=Identity(name="Ng"))
    pattern = _redactions((one, two), profile)
    assert anonymized(one, pattern) == "[hidden] présente une expérience en organisation"
    assert anonymized(two, pattern) == "[hidden] présente le rôle"
