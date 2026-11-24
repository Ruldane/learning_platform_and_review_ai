"""Describe the counts observed by Market Radar (D159, SPEC 1 and 18.3)."""

from app.agents.tools.radar_port import RadarSummary

UNAVAILABLE_TEXT = "Web search is unavailable. Try running the scan again later."
NO_MODEL_TEXT = "The scan needs a working model. Check your API key in Settings."
NO_ANALYSIS_TEXT = "The model did not respond, so the scan could not finish analyzing the postings."


def _count(number: int, one: str, many: str) -> str:
    return f"{number} {one if number == 1 else many}"


def counting_text(readable: int, blocked: int) -> str:
    """Report how many pages were processed, read, or blocked so far."""
    pages = _count(readable + blocked, "page", "pages")
    read = _count(readable, "page read", "pages read")
    return f"Processed {pages}. {read}, {blocked} blocked."


def summary_text(report: RadarSummary) -> str:
    """Report posting totals and count readable pages without postings separately."""
    offers = report.read_ok - report.not_postings
    parts = [
        _count(offers, "posting read", "postings read"),
        _count(report.blocked, "page blocked", "pages blocked"),
    ]
    if report.not_postings:
        parts.append(
            _count(report.not_postings, "page without a posting", "pages without postings")
        )
    parts.append(_count(report.analyzed, "posting analyzed", "postings analyzed"))
    return ", ".join(parts) + "."


def sample_text(report: RadarSummary) -> str | None:
    """Describe the ranking for a scan with fewer than 30 readable postings."""
    if not report.low_sample:
        return None
    offers = report.read_ok - report.not_postings
    if offers < 1:
        return "The scan needs readable postings to rank skills."
    count = _count(offers, "readable posting", "readable postings")
    return f"The ranking is based on a small sample of {count}."
