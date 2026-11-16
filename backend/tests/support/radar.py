"""Faux port du radar du marché (`FakeRadarStore`) en mémoire, idempotent comme le contrat (D159) :
une page déjà lue est rendue sans relecture ni recompte, une extraction déjà rangée n'est pas
refaite. Le « web » de la lecture est `sources` (lien normalisé → page). Aucun réseau ni LLM."""

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.agents.tools.radar_port import PostingPage, RadarContext, RadarSummary
from app.agents.tools.radar_schema import RadarFinding, link_key

RUN_ID = "00000000-0000-4000-8000-0000000000a1"
ROLE, ZONE = "Ingénieur IA", "Lyon"
LOW_SAMPLE = 30


@dataclass(frozen=True)
class Source:
    """Une page du faux web : son lien, ce que la lecture en rend."""

    url: str
    status: str  # "ok" ou "unreadable"
    text: str = ""


@dataclass
class FakeRadarStore:
    sources: dict[str, Source] = field(default_factory=dict)  # `link_key` → page
    role: str = ROLE
    zone: str = ZONE
    languages: tuple[str, ...] = ("fr",)
    read: list[PostingPage] = field(default_factory=list)
    saved: dict[str, RadarFinding] = field(default_factory=dict)  # offres rangées, par repère
    failed: list[str] = field(default_factory=list)
    candidates: list[str] | None = None
    queries: int | None = None
    fail_codes: list[str] = field(default_factory=list)
    fresh_reads: int = 0
    repeat_reads: int = 0  # `read_posting` appelé sur un lien déjà lu : ne doit jamais arriver
    extraction_calls: int = 0
    finalize_calls: int = 0
    block_reads_after: int | None = None  # la lecture se fige (arrêt du back) après n pages lues
    read_blocked: asyncio.Event = field(default_factory=asyncio.Event)  # posé quand elle se fige
    summary: RadarSummary | None = None

    def serve(self, *sources: Source) -> None:
        for source in sources:
            key = link_key(source.url)
            assert key is not None
            self.sources[key] = source

    async def context(self, user_id: str, run_id: str) -> RadarContext:
        extracted = frozenset(self.saved) | frozenset(self.failed)
        return RadarContext(
            run_id, self.role, self.zone, self.languages, list(self.read), extracted, len(self.read)
        )

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None:
        self.queries, self.candidates = queries, list(urls)

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage:
        key = link_key(url)
        for page in self.read:
            if link_key(page.url) == key:
                self.repeat_reads += 1
                return page
        if self.block_reads_after is not None and len(self.read) >= self.block_reads_after:
            self.read_blocked.set()
            await asyncio.Event().wait()
        source = self.sources.get(key or "")
        status, text = (source.status, source.text) if source else ("unreadable", "")
        page = PostingPage(
            f"r{len(self.read) + 1}",
            url,
            urlsplit(url).hostname or "",
            status,
            text,  # type: ignore[arg-type]
        )
        self.read.append(page)
        self.fresh_reads += 1
        return page

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None:
        self.extraction_calls += 1
        for item in items:
            self.saved.setdefault(item.ref, item)
        self.failed += [ref for ref in failed_refs if ref not in self.failed]

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary:
        self.finalize_calls += 1
        ok = sum(page.status == "ok" for page in self.read)
        not_postings = sum(not item.is_job_posting for item in self.saved.values())
        analyzed = sum(item.is_job_posting for item in self.saved.values())
        self.summary = RadarSummary(
            ok, len(self.read) - ok, not_postings, analyzed, ok < LOW_SAMPLE
        )
        return self.summary

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None:
        self.fail_codes.append(code)
