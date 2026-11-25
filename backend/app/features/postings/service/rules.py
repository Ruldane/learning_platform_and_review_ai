"""Pure posting rules (D118): key of a posting link, company key, resemblance of two titles,
sufficient text, ATS recognised by its domain (`detect_ats`, re-exported from
`app.agents.tools.ats_hosts`, shared with the `cv_review` path)."""

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.agents.tools.ats_hosts import ATS_HOSTS as ATS_HOSTS
from app.agents.tools.ats_hosts import detect_ats as detect_ats
from app.agents.tools.posting_schema import MIN_POSTING_CHARS as MIN_POSTING_CHARS
from app.agents.tools.posting_schema import MIN_POSTING_WORDS as MIN_POSTING_WORDS
from app.agents.tools.posting_schema import enough_text as enough_text
from app.core.skills import normalize_skill_name
from app.features.memory.service.upload import normalize_url

# Tracking parameters removed from a link: an entry ending in "_" is a prefix. "ref" and
# "src" are not (a deliberate deviation from the plan, D118): career sites put the posting there.
TRACKING_PARAMS = ("utm_", "gclid", "fbclid", "mc_cid", "mc_eid", "trk")
_DEFAULT_PORTS = {"http": 80, "https": 443}
LEGAL_SUFFIXES = (
    "sa",
    "sas",
    "sasu",
    "sarl",
    "eurl",
    "inc",
    "ltd",
    "llc",
    "gmbh",
    "ag",
    "bv",
    "plc",
    "corp",
)

PROBABLE_TITLE = 0.85  # same company and titles at 0.85 or more: probable duplicate
POSSIBLE_COSINE = 0.90  # best memory fragment at 0.90 or more: possible duplicate

_NON_ALNUM = re.compile(r"[^0-9a-z+#]+")


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return any(
        lowered.startswith(param) if param.endswith("_") else lowered == param
        for param in TRACKING_PARAMS
    )


def route_fragment(url: str) -> str:
    """The fragment of a site with anchor routing (`#/offre/1`, `#!/offre/1`): it identifies the
    posting and stays in the key. Any other fragment (`#postuler`) is removed."""
    fragment = urlsplit(url.strip()).fragment
    return fragment if fragment.startswith(("/", "!")) else ""


def posting_url_key(url: str) -> str:
    """The key of a posting link: `normalize_url` (raises `invalid_url` or `url_forbidden`), then
    "www." and the default port removed, tracking parameters removed, query sorted, final "/"
    removed, fragment removed except a route (`route_fragment`). A key passed again gives the same
    key. Two distinct postings never share a key: a real duplicate missed here is caught at the
    "probable" or "possible" level."""
    parts = urlsplit(normalize_url(url))
    netloc = parts.netloc
    if parts.port is not None and _DEFAULT_PORTS.get(parts.scheme) == parts.port:
        netloc = netloc.rsplit(":", 1)[0]
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(key)
    )
    path = parts.path.rstrip("/")
    return urlunsplit(
        (parts.scheme, netloc.removeprefix("www."), path, urlencode(query), route_fragment(url))
    )


def _words(text: str) -> list[str]:
    """Words of a name: `normalize_skill_name`, dots removed ("S.A.S."), then punctuation."""
    return _NON_ALNUM.sub(" ", normalize_skill_name(text).replace(".", "")).split()


def company_key(name: str) -> str:
    """The key of a company: without accents, case or punctuation, final legal forms removed
    ("Société Fictive SAS" → "societe fictive"). A name made only of legal forms keeps them."""
    words = _words(name)
    end = len(words)
    while end > 1 and words[end - 1] in LEGAL_SUFFIXES:
        end -= 1
    return " ".join(words[:end])


def title_similarity(a: str, b: str) -> float:
    """Resemblance (0..1) of two normalized titles, words sorted ("AI Product Engineer" and
    "Product Engineer AI": 1). An empty title resembles nothing."""
    left, right = " ".join(sorted(_words(a))), " ".join(sorted(_words(b)))
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()
