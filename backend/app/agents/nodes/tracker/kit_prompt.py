"""Ce que l'Assistant de suivi lit pour écrire une pièce (D142) : le profil, l'offre, la fiche et le
guide de style, chacun encadré par `untrusted` (17.4) ; la langue de l'offre."""

from app.agents.prompts.loader import untrusted
from app.agents.tools.cv_schema import Education, Experience, MasterProfileData, facts_of
from app.agents.tools.kit_schema import KitContext

MAX_POSTING_CHARS = 30_000
NO_CRITERIA = "Aucun critère repéré par l'analyse : relis l'offre."
NO_STYLE = "Aucun guide de style : écris sobrement, en phrases courtes."


def profile_text(profile: MasterProfileData) -> str:
    """Le profil validé : son nom, puis un fait par ligne `[identifiant] texte` (les expériences et
    formations avec leur période), ce que `fact_ids` cite."""
    dated: list[Experience | Education] = [*profile.experiences, *profile.education]
    periods = {
        item.id: f" ({item.start or '?'} → {item.end or 'en cours'})"
        for item in dated
        if item.start or item.end
    }
    lines = [f"Nom : {profile.identity.name}"]
    lines += [f"[{fact}] {text}{periods.get(fact, '')}" for fact, text in facts_of(profile).items()]
    return "\n".join(lines)


def card_text(ctx: KitContext) -> str:
    lines = [f"Entreprise : {ctx.company}", f"Intitulé exact du poste : {ctx.title}"]
    if ctx.contact:
        lines.append(f"Contact : {ctx.contact}")
    return "\n".join(lines)


def _eliminatory(ctx: KitContext) -> str:
    """Les critères éliminatoires que l'analyse a repérés (venus de l'offre : encadrés)."""
    texts = [item.text for item in ctx.analysis.eliminatory]
    return untrusted("\n".join(texts), "critères de l'offre") if texts else NO_CRITERIA


def prompt_vars(ctx: KitContext, style_guide: str) -> dict[str, object]:
    return {
        "language": ctx.language,
        "card": untrusted(card_text(ctx), "fiche de candidature"),
        "profile": untrusted(profile_text(ctx.profile), "profil de January"),
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "offre"),
        "style_guide": untrusted(style_guide, "guide de style")
        if style_guide.strip()
        else NO_STYLE,
        "eliminatory": _eliminatory(ctx),
    }
