from app.agents.tools.cv_schema import Identity, MasterProfileData, SkillFact
from app.agents.tools.linkedin_profile import LinkedInText, check_text


def test_rejects_unproven_figure_and_skill() -> None:
    profile = MasterProfileData(
        identity=Identity(name="Personne fictive"), skills=[SkillFact(name="Python")]
    )
    invented = LinkedInText(
        headline="Python",
        about="Je développe des scripts Python. J’ai géré 900 projets.",
        skills=["Python", "Kubernetes"],
    )
    found = check_text(invented, profile)
    assert [(claim.field, claim.term) for claim in found] == [
        ("about", "900"),
        ("skills", "Kubernetes"),
    ]
    reworked = LinkedInText(
        headline="Python", about="Je développe des scripts Python.", skills=["Python"]
    )
    assert check_text(reworked, profile) == []
