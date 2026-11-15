"""Ce que l'Intervieweur lit (D145) : l'offre, le dossier de l'entreprise, la version du CV envoyée,
les écarts connus et le profil, chacun encadré par `untrusted` (17.4) ; les échanges de l'entretien
(réponses de January comprises) le sont aussi. Un morceau absent est dit absent, jamais inventé."""

from app.agents.nodes.tracker.kit_prompt import profile_text
from app.agents.prompts.loader import untrusted
from app.agents.tools.cv_schema import CvContent
from app.agents.tools.interview_schema import Exchange, InterviewContext
from app.agents.tools.kit_schema import CompanyDossier

MAX_POSTING_CHARS = 12_000
NO_POSTING = "Aucune offre : entretien libre sur l'intitulé du poste, sans autre source."
NO_DOSSIER = "Aucun dossier sur l'entreprise."
NO_CV = "Aucune version de CV liée à cette candidature."
NO_GAPS = "Aucun écart connu."


def posting_block(ctx: InterviewContext) -> str:
    if ctx.posting_text and ctx.posting_text.strip():
        return untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "offre")
    if ctx.analysis is not None:
        lines = [f"Intitulé : {ctx.analysis.title}", f"Niveau : {ctx.analysis.level}"]
        lines += [f"- {item.text}" for item in ctx.analysis.requirements]
        return untrusted("\n".join(lines), "offre")
    return NO_POSTING


def dossier_lines(dossier: CompanyDossier) -> list[str]:
    lines = [
        f"Activité : {dossier.activity}",
        f"Produit : {dossier.product}",
        f"Culture : {dossier.culture}",
        f"Processus de recrutement : {dossier.interview_process}",
    ]
    if dossier.stack:
        lines.append("Technologies : " + ", ".join(dossier.stack))
    lines += [f"Actualité : {item.text}" for item in dossier.news]
    lines += [f"Point de vigilance : {point}" for point in dossier.watch_points]
    return lines


def dossier_block(ctx: InterviewContext) -> str:
    if ctx.dossier is None:
        return NO_DOSSIER
    return untrusted("\n".join(dossier_lines(ctx.dossier)), "dossier de l'entreprise")


def _cv_lines(cv: CvContent) -> list[str]:
    lines = [cv.name, *([cv.headline] if cv.headline else [])]
    for section in cv.sections:
        lines.append(f"## {section.title}")
        for entry in section.entries:
            head = " ".join(part for part in (entry.heading, entry.subheading, entry.dates) if part)
            lines += [head, *(f"- {line.text}" for line in entry.lines)]
        lines += [f"- {line.text}" for line in section.items]
    return lines


def cv_block(ctx: InterviewContext) -> str:
    if ctx.cv_content is None:
        return NO_CV
    return untrusted("\n".join(_cv_lines(ctx.cv_content)), "CV envoyé")


def gaps_block(ctx: InterviewContext) -> str:
    if not ctx.gaps:
        return NO_GAPS
    return untrusted("\n".join(f"- {gap}" for gap in ctx.gaps), "écarts connus")


def profile_block(ctx: InterviewContext) -> str:
    return untrusted(profile_text(ctx.profile), "profil de January")


def exchange_text(
    exchange: Exchange, *, with_note: bool = True, pending_follow_up: bool = False
) -> str:
    """Un échange tel que le modèle le lit : l'index (à partir de 0), la question, les réponses.
    `pending_follow_up` : la réponse à la relance est celle qu'on donne à lire, pas encore ici."""
    lines = [
        f"[index {exchange.index}] Question ({exchange.criterion}) : {exchange.question}",
        f"Réponse de January : {exchange.answer}",
    ]
    if exchange.follow_up:
        lines.append(f"Relance : {exchange.follow_up}")
    if exchange.follow_up and not pending_follow_up:
        lines.append(f"Réponse à la relance : {exchange.follow_up_answer or '(pas de réponse)'}")
    if with_note:
        note = "non notée (le modèle n'a pas répondu)" if exchange.unrated else f"{exchange.note}/5"
        lines.append(f"Note interne : {note}")
    return "\n".join(lines)


def exchanges_block(exchanges: list[Exchange]) -> str:
    return untrusted("\n\n".join(exchange_text(e) for e in exchanges), "échanges de l'entretien")


MODE_LABELS = {
    "behavioral": "comportemental",
    "technical": "technique",
    "case": "étude de cas",
    "mixed": "mixte (comportemental et technique)",
}
MODE_GUIDES = {
    "behavioral": (
        "Mode comportemental : des questions de mise en situation sur le parcours, la "
        "collaboration, les difficultés et les motivations ; une bonne réponse a une situation, "
        "une action et un résultat."
    ),
    "technical": (
        "Mode technique : des questions sur les outils, les concepts et les pratiques que le "
        "poste demande, du fondamental vers le plus fin."
    ),
    "case": (
        "Mode étude de cas : pose un scénario réaliste du poste dès la première question, puis "
        "des questions qui le font avancer ; January raisonne à voix haute, par écrit."
    ),
    "mixed": (
        "Mode mixte : environ la moitié de questions de comportement, l'autre moitié de "
        "questions techniques, en alternant."
    ),
}


def head_vars(ctx: InterviewContext) -> dict[str, object]:
    """Les variables du début du prompt, communes aux trois tâches de l'Intervieweur."""
    return {
        "role": untrusted(ctx.role, "intitulé du poste"),
        "mode_label": MODE_LABELS[ctx.mode],
        "duration": ctx.duration_min,
        "language": ctx.language,
    }
