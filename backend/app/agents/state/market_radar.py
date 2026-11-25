"""State of the `market_radar` graph (D159). The survey (links read, offers extracted, reads done)
is in the database, behind the `RadarStore` port: the read and extraction loops reread it on
each pass (SPEC 9.4); the state never keeps a lone counter. It only keeps the links
found by the search (the port does not return them), the outcome of each loop (computed on what the
port just returned) and the `run.completed` summary."""

from typing import TypedDict


class MarketRadarState(TypedDict, total=False):
    run_id: str
    urls: list[str]  # candidate links, no duplicates, 80 at most, in reading order
    reading_done: bool  # the read loop has nothing left to read
    extract_done: bool  # the extraction loop has nothing left to extract
    failed_batches: int  # extraction batches failed on the provider side (extraction stops at 2)
    summary: str  # `run.completed` summary
