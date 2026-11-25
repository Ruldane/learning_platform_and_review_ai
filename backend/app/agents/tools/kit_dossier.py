"""Check and rendering of the company file (SPEC 6.4, F16, D142). Code: the Verifier's role is
kept here, "no claim without a source read":

- a citation `[n]` whose page was not read is removed from the text;
- a text (activity, product, culture, interview process) that no longer cites any read page
  is emptied: the rendering says "Not found in the sources read.";
- a technology, a watch point or a news item without a valid citation is removed;
- a news item without a date, future-dated or older than 6 months is removed; likewise one whose all
  cited pages carry a known date older than 6 months (the model's date is not enough);
- questions to ask are questions, not claims: their invalid citations
  are removed; a question reduced to nothing is not rendered;
- the company size is not sourced: rendered as an estimate, omitted if unknown.

No logging here: the file is never written to a log (17.2)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.agents.tools.kit_schema import CompanyDossier, NewsItem, SourceRef

NEWS_MAX_AGE = timedelta(days=183)
UNSOURCED = "No evidence found in the sources read."
SIZES = {
    "startup": "startup",
    "sme": "small or medium-sized business",
    "large_company": "large company",
}
_CITATION = re.compile(r"\s*\[(\d+(?:\s*[,;]\s*\d+)*)\]")
_NUMBER = re.compile(r"\d+")


def _cleaned(text: str, valid: set[int]) -> tuple[str, int]:
    """`text` without the citations of unread pages, and the number of valid citations left."""
    kept = 0

    def keep(match: re.Match[str]) -> str:
        nonlocal kept
        numbers = [int(n) for n in _NUMBER.findall(match.group(1))]
        good = [n for n in numbers if n in valid]
        kept += len(good)
        return f" [{', '.join(str(n) for n in good)}]" if good else ""

    return _CITATION.sub(keep, text).strip(), kept


def _sourced(text: str, valid: set[int]) -> str:
    """The cleaned text, or empty if it cites no read page."""
    clean, kept = _cleaned(text, valid)
    return clean if kept else ""


@dataclass(frozen=True)
class Checked:
    """The checked file; `emptied`: the emptied texts, `dropped`: the removed items."""

    dossier: CompanyDossier
    emptied: int
    dropped: int


def _fresh(item: NewsItem, today: date) -> bool:
    return item.date is not None and today - NEWS_MAX_AGE <= item.date <= today


def _from_old_pages(text: str, page_dates: Sequence[date | None], today: date) -> bool:
    """All cited pages have a known date older than 6 months (a page without a date, or a
    recent page among them, leaves the news item in doubt)."""
    cited = [int(n) for match in _CITATION.findall(text) for n in _NUMBER.findall(match)]
    dates = [page_dates[n - 1] if n <= len(page_dates) else None for n in cited]
    return bool(dates) and all(d is not None and d < today - NEWS_MAX_AGE for d in dates)


def check_dossier(
    dossier: CompanyDossier, pages: int, today: date, *, page_dates: Sequence[date | None] = ()
) -> Checked:
    """A model's file, checked against the read `pages` (ranks 1 to `pages`), the day and the
    known date of each page (`page_dates`, in rank order)."""
    valid = set(range(1, pages + 1))
    texts = {
        name: _sourced(getattr(dossier, name), valid)
        for name in ("activity", "product", "culture", "interview_process")
    }
    stack = [s for s in (_sourced(item, valid) for item in dossier.stack) if s]
    points = [s for s in (_sourced(item, valid) for item in dossier.watch_points) if s]
    news = []
    for item in dossier.news:
        cited = _sourced(item.text, valid)
        if cited and _fresh(item, today) and not _from_old_pages(cited, page_dates, today):
            news.append(NewsItem(text=cited, date=item.date))
    questions = [_cleaned(question, valid)[0] for question in dossier.questions]
    checked = dossier.model_copy(
        update={
            **texts,
            "stack": stack,
            "watch_points": points,
            "news": news,
            "questions": questions,
        }
    )
    dropped = (
        len(dossier.stack) - len(stack)
        + len(dossier.watch_points) - len(points)
        + len(dossier.news) - len(news)
    )  # fmt: skip
    return Checked(checked, sum(1 for text in texts.values() if not text), dropped)


def has_content(dossier: CompanyDossier) -> bool:
    """At least one sourced text: otherwise the file is not produced."""
    texts = (dossier.activity, dossier.product, dossier.culture, dossier.interview_process)
    return any(texts) or bool(dossier.stack or dossier.news or dossier.watch_points)


def _section(title: str, body: str) -> str:
    return f"## {title}\n{body or UNSOURCED}"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_dossier(company: str, dossier: CompanyDossier, sources: list[SourceRef]) -> str:
    """The file in Markdown, with the list of read pages."""
    news = [
        f"{item.date.isoformat()} · {item.text}" if item.date else item.text
        for item in dossier.news
    ]
    asked = [text for text in dossier.questions if text.strip()]
    questions = "\n".join(f"{rank}. {text}" for rank, text in enumerate(asked, 1))
    size = SIZES.get(dossier.size)
    listed = [
        f"[{rank}] {source.title or source.url} — {source.url}"
        for rank, source in enumerate(sources, 1)
    ]
    parts = [
        f"# Company dossier for {company}",
        _section("Business", dossier.activity),
        _section("Product", dossier.product),
        _section("Technology", _bullets(dossier.stack)),
        _section("News from the last six months", _bullets(news)),
        _section("Culture", dossier.culture),
        _section("Interview process", dossier.interview_process),
        _section("Five questions to ask", questions),
        _section("Points to watch", _bullets(dossier.watch_points)),
        *([f"Estimated size (unsourced) · {size}"] if size else []),
        _section("Sources", "\n".join(listed)),
    ]
    return "\n\n".join(parts)
