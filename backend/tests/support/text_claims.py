"""Profil et aides des tests du contrôle des faits d'un texte (`text_claims`, 7.1)."""

from app.agents.tools.cv_schema import Education, Link, MasterProfileData
from app.agents.tools.text_claims import text_claims
from tests.support.cv_review import profile


def realistic() -> MasterProfileData:
    """Un profil avec dates, téléphone, email et lien : leurs chiffres ne sont pas des faits."""
    p = profile(
        line="Réduit de 30 % le temps de traitement avec Python",
        role="AI Engineer",
        skills=["Python", "Docker", "machine learning"],
        links=[Link(label="GitHub", url="https://github.com/camille-exemple")],
        education=[
            Education(degree="Master Informatique", school="Université Fictive", start="2015-09")
        ],
    )
    p.identity.phone = "06 12 34 56 78"
    p.identity.email = "camille.exemple@example.org"
    p.experiences[0].start, p.experiences[0].end = "2021-03", "2024-09"
    return p


P = realistic()
COMPANY, TITLE = "Société Fictive", "Lead Data Engineer"


def terms(text: str, *, allowed: tuple[str, ...] = ()) -> list[str]:
    return [c.term for c in text_claims(text, P, allowed=allowed)]
