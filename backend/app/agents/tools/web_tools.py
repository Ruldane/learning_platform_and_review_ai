"""Web tools of the agents (SPEC 10.1, 10.2, 9.5, D77): functions callable from a node,
which announce their call (`tool.called`) then return their outcome (`tool.result`); plus
`web_tools_for`, the same tools as `StructuredTool` for tool calling by the LLM.

Search and reading sit behind the `WebGateway` port (`GraphDeps.web`). The arguments of
`tool.called` carry the CLEANED query (the one the gateway actually sent, SPEC
17.3): the event of a failed search carries none. Any text from the web handed to a
model is framed by `untrusted()` (17.4)."""

from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.func import task
from pydantic import BaseModel, Field

from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.tools.web_port import PageRead, WebSearchResult
from app.core.errors import AppError
from app.core.played import played_by

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
    deps: GraphDeps,
    query: str,
    *,
    lang: str | None = None,
    time_range: str | None = None,
    agent: str,
) -> WebSearchResult:
    """Searches the web (SearXNG, Brave as fallback); `time_range` ("month"...) is passed to
    the gateway. Raises `AppError`: cap reached (429), no engine available (503),
    query empty once cleaned (422)."""

    async def search() -> WebSearchResult:
        found = await deps.web.search(
            deps.user_id, deps.session_id, query, lang=lang, time_range=time_range
        )
        call_id = _call(agent, "web_search", {"query": found.query, "lang": lang})
        provider = found.provider or "no provider"
        summary = f"{len(found.hits)} result(s) via {provider}"
        _result(agent, call_id, "web_search", ok=True, summary=summary)
        return found

    try:
        return await task(search)() if played_by(deps.user_id) else await search()
    except AppError as exc:
        call_id = _call(agent, "web_search", {"lang": lang})  # the raw query is never emitted
        _failed(agent, call_id, "web_search", exc)
        raise


async def web_read(deps: GraphDeps, url: str, *, agent: str) -> PageRead:
    """Reads a page: status `ok` or `unreadable` (with the reason). An unreadable page is
    never cited (SPEC 10.2). Raises `AppError`: page cap (429), address refused (422)."""

    async def read() -> PageRead:
        call_id = _call(agent, "web_read", {"url": url})
        try:
            page = await deps.web.read(deps.user_id, deps.session_id, url)
        except AppError as exc:
            _failed(agent, call_id, "web_read", exc)
            raise
        summary = "Read" if page.status == "ok" else f"Unreadable: {page.reason or '?'}"
        _result(agent, call_id, "web_read", ok=True, summary=summary)
        return page

    return await task(read)() if played_by(deps.user_id) else await read()


# --- Tools for tool calling by the LLM --------------------------------------------------------


class _SearchArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300, description="What to search for.")
    lang: str | None = Field(
        default=None, pattern=r"^[a-z]{2}$", description="Language of the results (fr, en...)."
    )


class _ReadArgs(BaseModel):
    url: str = Field(min_length=1, max_length=2000, description="http(s) address of the page.")


def search_agent_text(found: WebSearchResult) -> str:
    """Results handed to the model: titles and snippets come from the web, hence framed."""
    if not found.hits:
        return "No results."
    lines = []
    for number, hit in enumerate(found.hits, 1):
        star = " (preferred domain)" if hit.preferred else ""
        snippet = " ".join(hit.snippet.split())[:MAX_SNIPPET_CHARS]
        lines.append(f"{number}. {' '.join(hit.title.split())}{star}\n{hit.url}\n{snippet}")
    return untrusted("\n\n".join(lines), "search results")


def page_agent_text(page: PageRead) -> str:
    """Page handed to the model: title, author, date, language and text, all framed (17.4). An
    unreadable page has no text and must not be cited."""
    if page.status != "ok":
        return f"Unreadable page: {page.reason or 'unknown reason'}. Do not cite it."
    head = [
        f"Title: {' '.join((page.title or 'untitled').split())}",
        f"Author: {page.author or 'unknown'}",
        f"Date: {page.date or 'unknown'}",
        f"Language: {page.lang or 'unknown'}",
    ]
    label = f"page {page.source_id or 'no identifier'}"
    return untrusted("\n".join(head) + "\n\n" + page.text, label)


def web_tools_for(deps: GraphDeps, *, agent: str) -> list[BaseTool]:
    """`web_search` and `web_read`, bound to `deps` and to `agent`."""

    async def search(query: str, lang: str | None = None) -> str:
        return search_agent_text(await web_search(deps, query, lang=lang, agent=agent))

    async def read(url: str) -> str:
        return page_agent_text(await web_read(deps, url, agent=agent))

    return [
        StructuredTool.from_function(
            coroutine=search,
            name="web_search",
            description="Searches the web. Returns titles, addresses and snippets.",
            args_schema=_SearchArgs,
        ),
        StructuredTool.from_function(
            coroutine=read,
            name="web_read",
            description="Reads a web page. An unreadable page is never cited.",
            args_schema=_ReadArgs,
        ),
    ]
