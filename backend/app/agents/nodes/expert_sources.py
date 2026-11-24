"""Sources actually read and the expert catalogue, bounded to the session."""

from textwrap import shorten

from pydantic import HttpUrl, ValidationError

from app.agents.runtime.deps import GraphDeps
from app.agents.tools.expert_debate_port import ExpertCitation
from app.agents.tools.web_port import QUOTA_CODE, SEARCH_UNAVAILABLE_CODE, PageRead
from app.core.errors import AppError

MAX_READS = 4
EXCERPT = 500


class ExpertSource(ExpertCitation):
    material: str


def _source(page: PageRead, index: int) -> ExpertSource | None:
    if page.status != "ok" or page.source_id is None or not page.text or not page.text.strip():
        return None
    try:
        url = HttpUrl(page.url)
    except ValidationError:
        return None
    if url.username or url.password or not url.host:
        return None
    return ExpertSource(
        index=index,
        title=(page.title or url.host)[:180],
        url=url,
        material=page.text[:EXCERPT],
    )


async def debate_sources(deps: GraphDeps, question: str) -> list[ExpertSource]:
    query = shorten(question, width=300, placeholder="")
    if len(query) < 2:
        return []
    try:
        reply = await deps.web.search(deps.user_id, deps.session_id, query)
    except AppError as exc:
        if exc.code in {QUOTA_CODE, SEARCH_UNAVAILABLE_CODE, "search_query_empty"}:
            return []
        raise
    found: list[ExpertSource] = []
    for hit in reply.hits[:MAX_READS]:
        if any(str(source.url) == hit.url for source in found):
            continue
        try:
            page = await deps.web.read(deps.user_id, deps.session_id, hit.url)
        except AppError as exc:
            if exc.code == QUOTA_CODE:
                break
            if exc.status_code in {422, 503}:
                continue
            raise
        if source := _source(page, len(found) + 1):
            found.append(source)
    return found
