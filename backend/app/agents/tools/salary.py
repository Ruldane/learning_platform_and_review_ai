"""Question salariale (SPEC 1, 6, critère 18.3) : une prétention salariale n'est jamais écrite par
un agent, car elle engage January et qu'aucun fait du profil ne la dit. Le code reconnaît la
question (ce module) et impose une réponse vide : January la remplit elle-même.

La lecture est large exprès : un faux positif laisse une réponse vide (January la remplit), un
faux négatif écrirait un chiffre inventé."""

from app.agents.tools.posting_schema import normalize_term

# Mots et expressions (sans casse ni accent) qui font d'une question une question salariale.
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
    """La question parle de salaire, de rémunération, de prétentions, de package, de TJM ou de
    taux (français ou anglais), sans tenir compte de la casse ni des accents."""
    padded = f" {normalize_term(question)} "
    return any(f" {term} " in padded for term in SALARY_TERMS)
