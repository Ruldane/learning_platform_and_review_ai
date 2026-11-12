"""Outils web des agents (SPEC 10.1, 10.2, 9.5, D77) : des fonctions appelables depuis un nœud,
qui annoncent leur appel (`tool.called`) puis rendent leur issue (`tool.result`) ; plus
`web_tools_for`, les mêmes outils sous forme de `StructuredTool` pour l'appel d'outils par le LLM.

La recherche et la lecture sont derrière le port `WebGateway` (`GraphDeps.web`). Les arguments de
`tool.called` portent la requête NETTOYÉE (celle que la passerelle a réellement envoyée, SPEC
17.3) : l'événement d'une recherche en échec n'en porte aucune. Tout texte venu du web rendu à un
modèle est encadré par `untrusted()` (17.4)."""

from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.tools.web_port import PageRead, WebSearchResult
from app.core.errors import AppError

MAX_SNIPPET_CHARS = 300


def _call(agent: str, tool: str, args: dict[str, Any]) -> str:
    call_id = uuid4().hex
    emit("tool.called", {"call_id": call_id, "tool": tool, "args": args}, agent=agent)
    return call_id


def _result(agent: str, call_id: str, tool: str, *, ok: bool, summary: str) -> None:
    emit(
        "tool.result",
        {"call_id": call_id, "tool": tool, "ok": ok, "summary": summary},
        agent=agent,
    )


def _failed(agent: str, call_id: str, tool: str, exc: AppError) -> None:
    _result(agent, call_id, tool, ok=False, summary=exc.message)


async def web_search(
    deps: GraphDeps, query: str, *, lang: str | None = None, agent: str
) -> WebSearchResult:
    """Cherche sur le web (SearXNG, Brave en secours). Lève `AppError` : plafond atteint (429),
    aucun moteur disponible (503), requête vide une fois nettoyée (422)."""
    try:
        found = await deps.web.search(deps.user_id, deps.session_id, query, lang=lang)
    except AppError as exc:
        call_id = _call(agent, "web_search", {"lang": lang})  # la requête brute n'est jamais émise
        _failed(agent, call_id, "web_search", exc)
        raise
    call_id = _call(agent, "web_search", {"query": found.query, "lang": lang})
    provider = found.provider or "aucun fournisseur"
    summary = f"{len(found.hits)} résultat(s) via {provider}"
    _result(agent, call_id, "web_search", ok=True, summary=summary)
    return found


async def web_read(deps: GraphDeps, url: str, *, agent: str) -> PageRead:
    """Lit une page : statut `ok` ou `unreadable` (avec la raison). Une page illisible n'est
    jamais citée (SPEC 10.2). Lève `AppError` : plafond de pages (429), adresse refusée (422)."""
    call_id = _call(agent, "web_read", {"url": url})
    try:
        page = await deps.web.read(deps.user_id, deps.session_id, url)
    except AppError as exc:
        _failed(agent, call_id, "web_read", exc)
        raise
    if page.status == "ok":
        _result(agent, call_id, "web_read", ok=True, summary="Lue")
    else:
        _result(agent, call_id, "web_read", ok=True, summary=f"Illisible : {page.reason or '?'}")
    return page


# --- Outils pour l'appel d'outils par le LLM --------------------------------------------------


class _SearchArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300, description="Ce qu'on cherche.")
    lang: str | None = Field(
        default=None, pattern=r"^[a-z]{2}$", description="Langue des résultats (fr, en…)."
    )


class _ReadArgs(BaseModel):
    url: str = Field(min_length=1, max_length=2000, description="Adresse http(s) de la page.")


def search_agent_text(found: WebSearchResult) -> str:
    """Résultats rendus au modèle : titres et extraits viennent du web, donc encadrés."""
    if not found.hits:
        return "Aucun résultat."
    lines = []
    for number, hit in enumerate(found.hits, 1):
        star = " (domaine privilégié)" if hit.preferred else ""
        snippet = " ".join(hit.snippet.split())[:MAX_SNIPPET_CHARS]
        lines.append(f"{number}. {' '.join(hit.title.split())}{star}\n{hit.url}\n{snippet}")
    return untrusted("\n\n".join(lines), "résultats de recherche")


def page_agent_text(page: PageRead) -> str:
    """Page rendue au modèle : titre, auteur, date, langue et texte, tous encadrés (17.4). Une
    page illisible n'a pas de texte et ne doit pas être citée."""
    if page.status != "ok":
        return f"Page illisible : {page.reason or 'raison inconnue'}. Ne pas la citer."
    head = [
        f"Titre : {' '.join((page.title or 'sans titre').split())}",
        f"Auteur : {page.author or 'inconnu'}",
        f"Date : {page.date or 'inconnue'}",
        f"Langue : {page.lang or 'inconnue'}",
    ]
    label = f"page {page.source_id or 'sans identifiant'}"
    return untrusted("\n".join(head) + "\n\n" + page.text, label)


def web_tools_for(deps: GraphDeps, *, agent: str) -> list[BaseTool]:
    """`web_search` et `web_read`, liés à `deps` et à `agent`."""

    async def search(query: str, lang: str | None = None) -> str:
        return search_agent_text(await web_search(deps, query, lang=lang, agent=agent))

    async def read(url: str) -> str:
        return page_agent_text(await web_read(deps, url, agent=agent))

    return [
        StructuredTool.from_function(
            coroutine=search,
            name="web_search",
            description="Cherche sur le web. Rend des titres, adresses et extraits.",
            args_schema=_SearchArgs,
        ),
        StructuredTool.from_function(
            coroutine=read,
            name="web_read",
            description="Lit une page web. Une page illisible ne se cite jamais.",
            args_schema=_ReadArgs,
        ),
    ]
