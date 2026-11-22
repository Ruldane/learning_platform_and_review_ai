"""Le jeu de rôle choisit ses montants aux deux bornes du relevé figé."""

from app.agents.state.interview import InterviewState
from app.agents.tools.cv_lexicon import figures_in
from app.agents.tools.interview_schema import (
    Debrief,
    InterviewContext,
    PlannedQuestion,
    TurnDecision,
)
from app.agents.tools.negotiation import SalarySample

_QUESTIONS = {
    "fr": (
        "Quel élément concret justifie ta demande ?",
        "Si le fixe est plafonné, quelle condition de travail négocierais-tu ?",
        "De quelle responsabilité veux-tu parler pour étayer ta demande ?",
        "Comment présenterais-tu un compromis sur le périmètre du poste ?",
        "À quelle condition accepterais-tu une révision ultérieure de la rémunération ?",
        "Quelle information sur les avantages voudrais-tu vérifier ?",
        "Comment reformulerais-tu ton argument principal si le recruteur hésite ?",
        "Quelle alternative au fixe serait utile dans ce poste ?",
        "Comment résumerais-tu la proposition et ce qui reste à confirmer ?",
    ),
    "en": (
        "Which concrete example supports your request?",
        "If base pay is capped, which working condition would you negotiate?",
        "Which responsibility would you cite to support your request?",
        "How would you frame a compromise on the scope of the role?",
        "When would a later compensation review be useful to you?",
        "Which detail about the benefits would you verify?",
        "How would you reframe your strongest point if the recruiter hesitates?",
        "Which alternative to base pay would help in this role?",
        "How would you summarize the proposal and what remains to be confirmed?",
    ),
}


def _euros(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " €"


def salary_questions(sample: SalarySample, language: str, count: int) -> list[PlannedQuestion]:
    low, high = _euros(sample.minimum_eur), _euros(sample.maximum_eur)
    if language == "en":
        first = (
            f"Simulation. The radar shows {low} to {high} gross per year. In this exercise I start "
            f"at {low} and cap base pay at {high}. What would you ask for?"
        )
    else:
        first = (
            f"Simulation. Le radar indique de {low} à {high} bruts par an. Dans cet exercice, "
            f"je commence à {low} et je plafonne le fixe à {high}. Que demandes-tu ?"
        )
    remaining = _QUESTIONS[language]
    texts = [first, *remaining[: count - 2], remaining[-1]]
    return [PlannedQuestion(text=text, criterion="adequation", source="general") for text in texts]


def _recruiter_reply(amount: int, raised: bool, language: str) -> str:
    offer = _euros(amount)
    if language == "en":
        stance = "can raise the offer to" if raised else "am keeping the offer at"
        return f"In this simulation, I {stance} {offer} gross per year. How do you respond?"
    verb = "je peux porter" if raised else "je maintiens"
    return f"Dans cette simulation, {verb} l’offre à {offer} bruts par an. Comment réponds-tu ?"


def salary_decision(
    state: InterviewState, ctx: InterviewContext, decision: TurnDecision
) -> TurnDecision:
    sample = ctx.salary
    if sample is None:
        return decision.model_copy(update={"salary_move": False})
    if state["follow_up_open"]:
        return decision.model_copy(update={"salary_move": False, "follow_up": None})
    previously_raised = any(
        exchange.get("salary_raised") is True for exchange in state["exchanges"]
    )
    raised = (
        decision.salary_move
        and decision.note >= 3
        and not previously_raised
        and sample.minimum_eur < sample.maximum_eur
    )
    follow_up = None
    if raised or state["position"] == 0 or decision.follow_up is not None:
        offer = sample.maximum_eur if raised or previously_raised else sample.minimum_eur
        follow_up = _recruiter_reply(offer, raised, ctx.language)
    return decision.model_copy(update={"salary_move": raised, "follow_up": follow_up})


def without_unsourced_figures(debrief: Debrief, language: str) -> Debrief:
    """La fiche de simulation affiche les montants en dehors du commentaire libre du modèle."""
    if language == "en":
        fallback = "Link your request to a concrete responsibility in the role."
        improved = "I would like to discuss base pay in light of the responsibilities of the role."
    else:
        fallback = "Relie ta demande à une responsabilité concrète du poste."
        improved = "Je souhaite discuter du fixe au regard des responsabilités du poste."

    def safe(text: str) -> str:
        return fallback if figures_in(text) else text

    return debrief.model_copy(
        update={
            "strengths": [safe(text) for text in debrief.strengths],
            "fixes": [safe(text) for text in debrief.fixes],
            "improved_answer": improved
            if figures_in(debrief.improved_answer)
            else debrief.improved_answer,
            "expected": [
                item.model_copy(update={"points": [safe(point) for point in item.points]})
                for item in debrief.expected
            ],
        }
    )
