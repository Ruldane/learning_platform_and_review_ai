"""Honnêteté des pièces du kit (SPEC 1, 18.3, F16, D142) : du code, jamais l'agent. Une pièce écrite
au nom de January ne dit que ce que dit son profil :

- `flagged_terms` : les chiffres, outils, titres et noms propres que le profil ne dit pas
  (`text_claims`). `allowed` ne contient que des expressions entières : l'entreprise, l'intitulé
  exact de l'offre et le nom du contact, jamais un outil ni un chiffre de l'offre ;
- `length_problems` : les mots comptés par le code contre les bornes de chaque pièce ;
- `fix_answers` : une réponse de formulaire à une question salariale est vidée (la prétention
  engage January, aucun fait ne la dit), de même qu'une réponse qu'aucun fait du profil n'appuie.

Les problèmes d'un premier essai repartent au modèle une seule fois (`retry_message`) ; ce qui
reste après l'essai rend la pièce « à vérifier »."""

from dataclasses import dataclass

from app.agents.tools.kit_schema import Draft, FormAnswer, FormAnswers, KitContext
from app.agents.tools.salary import is_salary_question
from app.agents.tools.text_claims import text_claims

RETRY = (
    "N'écris rien qui ne soit pas dans le profil : {terms}. Ces éléments ne figurent pas dans le "
    "profil de January. Réécris la pièce sans eux, avec ce que dit son profil seulement."
)
LENGTH_RETRY = "Respecte les longueurs : {problems}"


def allowed_phrases(ctx: KitContext) -> list[str]:
    """Les expressions entières que le texte peut écrire : entreprise, intitulé, contact."""
    return [phrase for phrase in (ctx.company, ctx.title, ctx.contact) if phrase]


def flagged_terms(draft: Draft, ctx: KitContext) -> list[str]:
    """Les termes que le profil ne dit pas, sans doublon, dans l'ordre des parties du texte."""
    allowed = allowed_phrases(ctx)
    terms: list[str] = []
    for text in draft.parts().values():
        for claim in text_claims(text, ctx.profile, allowed=allowed):
            if claim.term not in terms:
                terms.append(claim.term)
    return terms


def word_counts(draft: Draft) -> dict[str, int]:
    """Les mots de chaque partie qui a une borne (comptés aux blancs)."""
    parts = draft.parts()
    return {name: len(parts[name].split()) for name in draft.limits}


def meta_words(draft: Draft) -> int | dict[str, int] | None:
    """`meta.words` : le compte d'une pièce à une seule partie bornée, sinon un par partie."""
    counts = word_counts(draft)
    if not counts:
        return None
    return next(iter(counts.values())) if len(counts) == 1 else counts


def _bounds(low: int, high: int) -> str:
    return f"de {low} à {high} mots" if low > 1 else f"{high} mots au plus"


def length_problems(draft: Draft) -> list[str]:
    counts = word_counts(draft)
    return [
        f"le champ `{name}` fait {counts[name]} mots, il doit en faire {_bounds(low, high)}."
        for name, (low, high) in draft.limits.items()
        if not low <= counts[name] <= high
    ]


@dataclass(frozen=True)
class Review:
    terms: list[str]  # ce que le profil ne dit pas
    problems: list[str]  # longueurs hors bornes

    def __bool__(self) -> bool:
        return bool(self.terms or self.problems)


def review(draft: Draft, ctx: KitContext) -> Review:
    return Review(flagged_terms(draft, ctx), length_problems(draft))


def retry_message(found: Review) -> str:
    """Le message du nouvel essai : les termes nommés, les longueurs hors bornes."""
    parts = []
    if found.terms:
        parts.append(RETRY.format(terms=", ".join(found.terms)))
    if found.problems:
        parts.append(LENGTH_RETRY.format(problems=" ".join(found.problems)))
    return "\n".join(parts)


def fix_answers(draft: FormAnswers, fact_ids: set[str]) -> FormAnswers:
    """Les réponses vérifiées par le code : salariale ou sans fait valide, la réponse est vidée ;
    sinon seuls les faits valides restent cités."""
    items = []
    for item in draft.items:
        valid = [fact for fact in dict.fromkeys(item.fact_ids) if fact in fact_ids]
        if is_salary_question(item.question) or not valid:
            items.append(FormAnswer(question=item.question, answer="", fact_ids=[]))
        else:
            items.append(FormAnswer(question=item.question, answer=item.answer, fact_ids=valid))
    return FormAnswers(items=items)
