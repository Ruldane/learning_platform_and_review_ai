"""English follow-up templates (SPEC 6.2, D140) use the company, role, dates, and contact name.
A missing date is omitted. A ready kit draft takes precedence over the 7-day and 14-day
templates and keeps the saved wording. Drafts are never logged."""

from datetime import date
from urllib.parse import quote

from app.agents.tools.kit_schema import split_followups
from app.db.models.applications import ReminderKind

LINKEDIN_SEARCH = "https://www.linkedin.com/search/results/people/?keywords="
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_KIT_INDEX: dict[ReminderKind, int] = {"linkedin_7": 0, "email_14": 1}

_TEMPLATES: dict[ReminderKind, str] = {
    "linkedin_7": (
        "{hello}\n\nI applied{applied} for the {title} position at {company}. I wanted to follow "
        "up to check that my application reached you, and to see whether you need anything more "
        "from me. I remain very interested in this role.\n\nThank you in advance for your reply."
    ),
    "email_14": (
        "Subject: My application for the {title} position: follow-up\n\n{hello}\n\nI am "
        "following up on my application{applied} for the {title} position at {company}, which "
        "has not received a reply yet. I am still interested in the role and available to talk "
        "at your convenience.\n\nBest regards,"
    ),
    "thanks": (
        "{hello}\n\nThank you for the time you gave me during our interview{interview} for the "
        "{title} position at {company}. Our conversation strengthened my interest in the role. "
        "I remain at your disposal for any further information.\n\nBest regards,"
    ),
    "news_7": (
        "{hello}\n\nI am following up on our interview{interview} for the {title} position at "
        "{company}. Would you have any news on the next steps of the process?\n\n"
        "Thank you in advance for your reply.\n\nBest regards,"
    ),
    "close_21": (
        "{company} hasn't replied to your application{applied} for {title}. Mark as No answer?"
    ),
}


def _when(day: date | None) -> str:
    if day is None:
        return ""
    return f" on {day.day} {_MONTHS[day.month - 1]} {day.year}"


def _hello(contact_name: str | None) -> str:
    first = (contact_name or "").split()
    return f"Hello {first[0]}," if first else "Hello,"


def kit_followup(content: str, kind: ReminderKind) -> str | None:
    """Le texte de la pièce « relances » du kit pour cette relance : le courriel de 7 jours est
    avant la première ligne `---`, celui de 14 jours après (`split_followups`, la règle du graphe) ;
    `None` s'il manque."""
    index = _KIT_INDEX.get(kind)
    if index is None:
        return None
    return split_followups(content)[index] or None


def linkedin_search_url(company: str, title: str) -> str:
    """La recherche de personnes LinkedIn « entreprise + poste visé » ; jamais journalisée."""
    return LINKEDIN_SEARCH + quote(f"{company} {title}", safe="")


def draft_for(
    kind: ReminderKind,
    *,
    company: str,
    title: str,
    contact_name: str | None,
    applied_on: date | None,
    interview_on: date | None,
    kit_followup: str | None,
) -> str:
    """Return the draft the user can copy."""
    if kit_followup and kind in _KIT_INDEX:
        return kit_followup
    return _TEMPLATES[kind].format(
        hello=_hello(contact_name),
        company=company,
        title=title,
        applied=_when(applied_on),
        interview=_when(interview_on),
    )
