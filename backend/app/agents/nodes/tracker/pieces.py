"""Les pièces du kit de candidature écrites par l'Assistant de suivi (SPEC 6.4, F16, D142) : `cv`
(sans modèle), `letter`, `linkedin`, `followups`, `pitch` et `form_answers`, une branche chacune.

Une pièce de texte : profil, offre, fiche et guide de style dans le prompt (`untrusted`), puis le
contrôle du code (`honesty`) : `text_claims` sur chaque partie et mots comptés. Un problème
renvoie la pièce au modèle **une seule fois**, avec les termes nommés (« n'écris rien qui ne soit
pas dans le profil : … ») ; ce qui reste après l'essai rend la pièce « à vérifier » (`meta.flags`
les termes, `meta.words` le compte). `form_answers` : une réponse à une question salariale est
vidée par le code (`meta.salary`), de même qu'une réponse sans fait valide du profil.

`meta` de chaque pièce de texte : `language`, `words` ; `flags` si des termes restent. Un échec de
l'agent (`failed`, motif lisible) n'arrête pas les autres branches."""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.nodes.tracker.honesty import (
    Review,
    fix_answers,
    meta_words,
    retry_message,
    review,
)
from app.agents.nodes.tracker.intake import AGENT
from app.agents.nodes.tracker.kit_common import Node, Piece, finish, guarded
from app.agents.nodes.tracker.kit_prompt import prompt_vars
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.cv_schema import facts_of
from app.agents.tools.kit_schema import (
    Draft,
    Followups,
    FormAnswers,
    KitContext,
    KitKind,
    KitStatus,
    Letter,
    LinkedInMessages,
    Pitch,
)
from app.core.errors import AppError

PIECE_LIMIT_S = 240  # deux demandes au plus, chacune avec ses nouveaux essais (GLM)
NO_CV = "Lance la revue de CV de cette offre pour obtenir ton CV ciblé."


@dataclass(frozen=True)
class TextSpec:
    kind: KitKind
    schema: type[Draft]
    request: str  # le message de l'utilisatrice : le marqueur des tests
    intent: str


SPECS: dict[str, TextSpec] = {
    spec.kind: spec
    for spec in (
        TextSpec("letter", Letter, "Rédige la lettre de motivation.", "j'écris la lettre"),
        TextSpec(
            "linkedin", LinkedInMessages, "Rédige l'invitation et le message LinkedIn.",
            "j'écris les messages LinkedIn",
        ),
        TextSpec(
            "followups", Followups, "Rédige les deux courriels de relance.",
            "j'écris les relances",
        ),
        TextSpec("pitch", Pitch, "Rédige le pitch de présentation.", "j'écris le pitch"),
        TextSpec(
            "form_answers", FormAnswers, "Rédige les réponses aux questions éliminatoires.",
            "je prépare les réponses du formulaire",
        ),
    )
}  # fmt: skip


@dataclass(frozen=True)
class Written:
    draft: Draft
    found: Review  # ce qui reste après le seul nouvel essai


def _fixed(draft: Draft, ctx: KitContext) -> Draft:
    """Le brouillon vérifié par le code avant le contrôle des faits (réponses de formulaire)."""
    if isinstance(draft, FormAnswers):
        return fix_answers(draft, set(facts_of(ctx.profile)))
    return draft


async def write(deps: GraphDeps, ctx: KitContext, spec: TextSpec) -> Written:
    """Le brouillon de la pièce, contrôlé ; un seul nouvel essai avec les problèmes nommés."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, mode=spec.kind, **prompt_vars(ctx, deps.settings.style_guide))
    messages = [SystemMessage(prompt), HumanMessage(spec.request)]

    async def ask(conversation: list[Any]) -> Draft:
        return await structured_call(
            model, spec.schema, conversation, agent=AGENT, step=spec.kind, intent=spec.intent
        )

    first = await ask(messages)
    draft = _fixed(first, ctx)
    found = review(draft, ctx)
    if not found:
        return Written(draft, found)
    retry = [*messages, AIMessage(first.model_dump_json()), HumanMessage(retry_message(found))]
    try:
        again = _fixed(await ask(retry), ctx)
    except AppError as exc:
        if exc.code != "structured_output_invalid":
            raise
        return Written(draft, found)  # le second essai est illisible : le premier, à vérifier
    return Written(again, review(again, ctx))


def piece_of(written: Written) -> Piece:
    """La pièce rangée : `ready` si rien ne reste, sinon `to_check` avec de quoi relire."""
    draft = written.draft
    meta: dict[str, Any] = {"language": "en"}
    words = meta_words(draft)
    if words is not None:
        meta["words"] = words
    if written.found.terms:
        meta["flags"] = written.found.terms
    blank = False
    if isinstance(draft, FormAnswers):
        states = [item.state for item in draft.items]
        meta["items"] = [
            {"question": i.question, "answer": i.answer, "fact_ids": i.fact_ids, "state": i.state}
            for i in draft.items
        ]
        meta["salary"] = "salary" in states
        blank = any(state != "ok" for state in states)
    status: KitStatus = "to_check" if written.found or blank else "ready"
    return Piece(status, draft.render(), meta)


def make_text_piece(deps: GraphDeps, kind: str) -> Node:
    spec = SPECS[kind]

    async def piece(state: ApplicationKitState) -> ApplicationKitState:
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])

        async def work() -> Piece:
            return piece_of(await write(deps, ctx, spec))

        done = await guarded(PIECE_LIMIT_S, work)
        return await finish(deps, ctx.application_id, spec.kind, done, agent=AGENT)

    piece.__name__ = f"piece_{kind}"
    return node_timeout(PIECE_LIMIT_S + 60)(piece)


def make_cv(deps: GraphDeps) -> Node:
    @node_timeout()
    async def cv(state: ApplicationKitState) -> ApplicationKitState:
        """La version de CV prête la plus récente de l'offre : aucun modèle, aucun contrôle."""
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])
        version = ctx.cv_version
        if version is None:
            done = Piece("to_check", NO_CV)
        else:
            content = f"CV ciblé : version n° {version.number}"
            done = Piece("ready", content, {"version_id": version.version_id})
        return await finish(deps, ctx.application_id, "cv", done, agent=AGENT)

    return cv
