"""LinkedIn text limited to the facts of the master profile."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.text_claims import text_claims
from app.core.skills import normalize_skill_name

Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Headline = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=220)]
About = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2600)]


class LinkedInText(BaseModel):
    headline: Headline
    about: About
    skills: list[Skill] = Field(default_factory=list, max_length=20)


class LinkedInClaim(BaseModel):
    field: Literal["headline", "about", "skills"]
    term: str


def check_text(text: LinkedInText, profile: MasterProfileData) -> list[LinkedInClaim]:
    """The same check as the CV, plus skills chosen from the profile."""
    known = {normalize_skill_name(skill.name) for skill in profile.skills}
    return [
        *(
            LinkedInClaim(field="headline", term=claim.term)
            for claim in text_claims(text.headline, profile)
        ),
        *(
            LinkedInClaim(field="about", term=claim.term)
            for claim in text_claims(text.about, profile)
        ),
        *(
            LinkedInClaim(field="skills", term=name)
            for name in text.skills
            if normalize_skill_name(name) not in known
        ),
    ]
