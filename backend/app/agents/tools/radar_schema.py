"""Schemas of the market radar (P5, P6): the search queries, built by the code (no model writes
a query), and the Analyst's output, an extraction per batch of five postings.

Nothing here invents data: the queries only contain the role, the area and public job
board sites; the extraction is checked by the code (`analyst_radar`) before being stored."""

import re
from collections.abc import Sequence
from itertools import zip_longest
from typing import NamedTuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field

from app.agents.tools.posting_schema import CheckpointPostingLevel

# Public posting pages (SPEC 10): one targeted query per site.
SITE_HINTS = (
    "jobs.lever.co",
    "boards.greenhouse.io",
    "welcometothejungle.com",
    "jobs.ashbyhq.com",
)
MAX_QUERIES = 12  # the query cap of a session: the radar is its only searcher
SITE_RESERVE = 2  # targeted queries kept even when the languages fill the cap
BATCH = 5  # postings per Analyst call (at most 10 calls for 50 postings)
TEXT_MAX = 4000  # characters of a posting shown to the Analyst
READ_BATCH = 10  # links read per pass of the reading loop
READ_PARALLEL = 5  # simultaneous reads
TIME_RANGE = "month"  # search window: the postings of the month


class RadarSearch(NamedTuple):
    """A radar query and the language of the expected results (`None`: no preference)."""

    query: str
    lang: str | None


_DIGITS = re.compile(r"\d+")


def salary_in_text(salary: str | None, text: str) -> str | None:
    """The salary noted by the model, kept only if each of its numbers appears in the
    text of the posting (whole number of digits: 45 is not 450). Same rule as
    `radar.service.rules.salary_shown` (the engine imports no feature; a test checks
    they agree). An empty salary or one without digits: `None`."""
    figures = _DIGITS.findall(salary or "")
    if not figures:
        return None
    present = set(_DIGITS.findall(text))
    return (salary or "").strip() if all(figure in present for figure in figures) else None


_TRACKING = ("utm_", "gclid", "fbclid", "mc_cid", "mc_eid", "trk")
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return any(
        lowered.startswith(param) if param.endswith("_") else lowered == param
        for param in _TRACKING
    )


def link_key(url: str) -> str | None:
    """The key of a posting link to deduplicate the results and follow the reads: the same as
    `postings.service.rules.posting_url_key` (the engine imports no feature; a test checks
    they agree on a table of links). `None`: invalid link (other scheme, no host,
    with credentials); it is never read."""
    try:
        parts = urlsplit(url.strip())
        host, port = parts.hostname, parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS or not host:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    netloc = host.lower() if ":" not in host else f"[{host.lower()}]"
    if port is not None and _DEFAULT_PORTS[scheme] != port:
        netloc = f"{netloc}:{port}"
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(key)
    )
    fragment = parts.fragment if parts.fragment.startswith(("/", "!")) else ""
    return urlunsplit(
        (scheme, netloc.removeprefix("www."), parts.path.rstrip("/"), urlencode(query), fragment)
    )


def _clean(text: str) -> str:
    return " ".join(text.split())


# General queries per language, from the most common to the rarest (`{r}` role, `{w}` area).
# The French phrases below are real search queries for French-language results: kept in French.
# Each variant brings back other postings than the previous ones: an engine only returns ten
# results per query and SearXNG has no second page here (D164).
_GENERIC = {
    "fr": (
        "offre d'emploi {r}{w}",
        "{r}{w} recrutement CDI",
        "{r} H/F{w}",
        "{r}{w} emploi",
        "{r} offre{w}",
        "{r}{w} poste à pourvoir",
        "{r}{w} on recrute",
        "{r}{w} postuler",
    ),
    "other": ("{r} job{w}", "{r}{w} hiring", "{r}{w} careers", "{r}{w} apply"),
}


def radar_searches(role: str, zone: str, languages: Sequence[str]) -> list[RadarSearch]:
    """The queries of the survey, `MAX_QUERIES` at most, without duplicates. First the general
    queries (in French "offre d'emploi {role} {area}", "{role} H/F {area}"...; for any other
    language "{role} job {area}", "{role} {area} hiring"...), the languages alternating so
    that the cap deprives none of them; then "{role} {area} site:{site}" for each job board,
    which an engine serves poorly and which therefore come last (at least `SITE_RESERVE` remain).
    Without a role: none."""
    role, zone = _clean(role), _clean(zone)
    if not role:
        return []
    where = f" {zone}" if zone else ""
    langs = [lang for lang in dict.fromkeys(languages) if lang] or ["fr"]
    lists = [
        [(lang, t.format(r=role, w=where)) for t in _GENERIC["fr" if lang == "fr" else "other"]]
        for lang in langs
    ]
    generic = [
        RadarSearch(q, lang) for rank in zip_longest(*lists) for lang, q in filter(None, rank)
    ]
    found = _unique(generic)[: MAX_QUERIES - SITE_RESERVE]
    found += [RadarSearch(f"{role}{where} site:{hint}", langs[0]) for hint in SITE_HINTS]
    return _unique(found)[:MAX_QUERIES]


def _unique(searches: Sequence[RadarSearch]) -> list[RadarSearch]:
    seen: set[str] = set()
    unique: list[RadarSearch] = []
    for search in searches:
        if search.query not in seen:
            seen.add(search.query)
            unique.append(search)
    return unique


def radar_queries(role: str, zone: str, languages: Sequence[str]) -> list[str]:
    """The text of the `radar_searches` queries."""
    return [search.query for search in radar_searches(role, zone, languages)]


class SkillNeedLite(BaseModel):
    """A skill requested by the posting; `required`: demanded rather than wished."""

    name: str = Field(min_length=2, max_length=80)
    required: bool


class RadarItem(BaseModel):
    """The extraction of a posting. `ref`: the posting's marker in the batch (`p1` to `p5`); the
    port receives it rewritten with the page's marker (`PostingPage.ref`). `is_job_posting`
    false: the page is not a posting, the rest is ignored."""

    ref: str = Field(pattern=r"^p[1-5]$")
    is_job_posting: bool
    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: CheckpointPostingLevel = "unknown"
    remote: str | None = Field(default=None, max_length=60)
    salary: str | None = Field(default=None, max_length=80)
    skills: list[SkillNeedLite] = Field(default_factory=list, max_length=15)
    tools: list[str] = Field(default_factory=list, max_length=15)


class RadarBatch(BaseModel):
    items: list[RadarItem] = Field(max_length=BATCH)


class RadarFinding(RadarItem):
    """The extraction of a posting stored under the marker of its **page** (`PostingPage.ref`:
    `p1`, `p12`, `r1`...), not under the marker of the batch of five (`RadarItem.ref`, `p1` to
    `p5`). This is what the port receives: `ref` is free there (1 to 16 characters), so that a
    validation re-read, here or in the adapter, never fails on a page marker."""

    ref: str = Field(min_length=1, max_length=16)
