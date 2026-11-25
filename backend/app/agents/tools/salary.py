"""Salary question (SPEC 1, 6, criterion 18.3): an agent never writes a salary expectation, because
it binds January and no profile fact states it. The code recognizes the question (this module) and
forces an empty answer: January fills it in herself.

The reading is deliberately broad: a false positive leaves an empty answer (January fills it in), a
false negative would write an invented figure."""

from app.agents.tools.posting_schema import normalize_term

# Words and expressions (without case or accent) that make a question a salary question.
SALARY_TERMS: frozenset[str] = frozenset(
    {
        "salaire",
        "salaires",
        "salarial",
        "salariale",
        "salariales",
        "salariaux",
        "remuneration",
        "remunerations",
        "pretention",
        "pretentions",
        "package",
        "tjm",
        "salary",
        "compensation",
        "taux journalier",
        "taux horaire",
        "brut annuel",
        "daily rate",
        "day rate",
        "hourly rate",
        "expected pay",
        "desired pay",
        "pay range",
        "pay expectation",
        "pay expectations",
        "annual pay",
        "gross annual",
    }
)


def is_salary_question(question: str) -> bool:
    """The question talks about salary, pay, expectations, package, day rate or rate
    (French or English), regardless of case and accents."""
    padded = f" {normalize_term(question)} "
    return any(f" {term} " in padded for term in SALARY_TERMS)
