"""What a text may say without it being a fact from January (`text_claims` check): her own
contact details (phone, email, profile links), the days of the month ("le 12 novembre") and
the quoted expressions of the posting (company, title, contact). Each mask replaces the text
with spaces of the same length: the positions of the other terms do not move."""

import re
from collections.abc import Sequence

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import normalize_term

# Words that designate the posting: "votre poste de X", "the X position".
POSTING_WORDS = frozenset(
    "poste offre role candidature opportunite position opening job".split()  # noqa: SIM905
)
# What precedes a posting word when it speaks of the other side's posting, not January's job.
DETERMINERS = frozenset("votre vos ce cette le la l your this the".split())  # noqa: SIM905
# A word that precedes a company or contact name: "chez X", "at X", "avec X".
EMPLOYER_WORDS = frozenset(
    """chez at pour for avec with rejoindre rejoint join joined joining aupres bonjour hello dear
    madame monsieur""".split()  # noqa: SIM905
)
# Words that attach what follows to January: the expression is no longer the posting's.
SELF_WORDS = frozenset(
    """mon ma mes my actuel actuelle current precedent precedente previous j je i""".split()  # noqa: SIM905
)
# The text gives itself a title (normalised words): "en tant que", "je suis", "j'étais"...
SELF_CUES = (
    ("en", "tant", "que"),
    ("en", "qualite", "de"),
    ("je", "suis"),
    ("j", "etais"),
    ("j", "ai", "ete"),
    ("j", "ai", "occupe"),
    ("j", "ai", "exerce"),
    ("etant",),
    ("ayant", "ete"),
    ("comme",),
    ("mon", "poste"),
    ("mon", "role"),
    ("mon", "experience"),
    ("as",),
    ("i", "am"),
    ("i", "m"),
    ("i", "was"),
    ("i", "ve", "been"),
    ("i", "have", "been"),
    ("worked", "as"),
    ("served", "as"),
    ("working", "as"),
    ("my", "role"),
    ("my", "position"),
    ("my", "job"),
    ("my", "experience"),
)
_MIN_PHONE_DIGITS = 6
CITING_WINDOW = 6  # words before the expression, in the same clause
_CLAUSE_BREAK = re.compile(r"[.,;!?\n]")
# French and English month names: both stay (letters and documents stored before the switch).
_FRENCH_MONTHS = "janvier février fevrier mars avril mai juin juillet août aout septembre octobre"
_FRENCH_MONTHS += " novembre décembre decembre"
# Lowercase "may" is the verb: only "May" is a month.
_ENGLISH_MONTHS = (
    "january|february|march|april|(?-i:May)|june|july|august|september|october|november|december"
)
_MONTHS = f"{_FRENCH_MONTHS.replace(' ', '|')}|{_ENGLISH_MONTHS}"
_DAY_MONTH = re.compile(
    rf"(?<!\w)\d{{1,2}}(?:er|st|nd|rd|th)?\s+(?:(?:de|of)\s+)?(?:{_MONTHS})(?!\w)", re.IGNORECASE
)
# "November 12, 2026", "March 5th", "May 3.": a number followed by a noun ("March 5 clients")
# is a count, not a day.
_MONTH_DAY = re.compile(
    rf"(?<!\w)(?:{_ENGLISH_MONTHS})\s+\d{{1,2}}"
    r"(?:(?:st|nd|rd|th)(?!\w)|(?=\s*(?:[,.;!?\n]|$))|(?=\s+\d{4}))",
    re.IGNORECASE,
)
_NUMERIC_DATE = re.compile(r"(?<![\d/.])(\d{1,2}[/.]\d{1,2}[/.])(\d{4})(?!\d)")
_PARENTHESIS = re.compile(r"\([^)]*\)")


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group())


def mask_dates(text: str) -> str:
    """The days of the month are masked ("12 novembre", "November 12", "12/11/"): a date
    is not a profile figure. A year stays: it is compared with the profile's dates."""
    text = _DAY_MONTH.sub(_blank, text)
    text = _MONTH_DAY.sub(_blank, text)
    return _NUMERIC_DATE.sub(lambda m: " " * len(m.group(1)) + m.group(2), text)


def _literal(value: str, *, phone: bool = False) -> str:
    """The pattern of a contact written as is: a phone number reads with
    any separators (spaces, dots, dashes) between its digits."""
    if phone:
        digits = re.sub(r"\D", "", value)
        return r"[\s.\-]?".join(digits) if len(digits) >= _MIN_PHONE_DIGITS else ""
    link = re.sub(r"^\w+://", "", value.strip()).rstrip("/")
    return re.escape(link) if link else ""


def mask_own_contacts(text: str, profile: MasterProfileData) -> str:
    """The phone, the email and the profile's links, written in the text (signature), are
    masked: their digits are never a reference."""
    patterns = [_literal(profile.identity.phone or "", phone=True)]
    patterns.append(_literal(profile.identity.email or ""))
    patterns += [_literal(link.url) for link in profile.links]
    patterns += [_literal(project.link or "") for project in profile.projects]
    for pattern in filter(None, patterns):
        text = re.sub(rf"(?<!\w)(?:\w+://)?{pattern}/?", _blank, text, flags=re.IGNORECASE)
    return text


def _has_cue(words: Sequence[str]) -> bool:
    """An attribution formula (`SELF_CUES`) appears among `words`."""
    return any(
        tuple(words[rank : rank + len(cue)]) == cue
        for cue in SELF_CUES
        for rank in range(len(words))
    )


def _cites_posting(before: str, after: str) -> bool:
    """The expression speaks of the posting: "votre poste de X" (a posting word, preceded by
    "votre", "le"..., within the 6 words before, with no "mon", "actuel", "je" or attribution
    formula between the posting word and the expression) or "the X role" (a determiner
    before, a posting word right after)."""
    words = normalize_term(_CLAUSE_BREAK.split(before)[-1]).split()
    following = normalize_term(_CLAUSE_BREAK.split(after)[0]).split()[:1]
    if words[-1:] and words[-1] in DETERMINERS and following and following[0] in POSTING_WORDS:
        return True
    recent = words[-(CITING_WINDOW + 1) :]
    for rank, word in enumerate(recent):
        if word not in POSTING_WORDS or rank == 0 or recent[rank - 1] not in DETERMINERS:
            continue
        if not _has_cue(recent) and not SELF_WORDS & set(recent[rank + 1 :]):
            return True
    return False


def _after_employer_word(before: str) -> bool:
    words = normalize_term(_CLAUSE_BREAK.split(before)[-1]).split()
    return bool(words) and words[-1] in EMPLOYER_WORDS


def mask_phrases(text: str, phrases: Sequence[str]) -> str:
    """Removes from the text, where they appear, the whole expressions of `phrases` (company,
    exact job title, contact name; without the parenthesis "(H/F)"), but only
    when the text cites them: right after "chez", "at", "avec"... (a company, a
    contact) or as the other side's posting (`_cites_posting`). Elsewhere they stay read:
    "en tant que Lead Data", "Je travaille avec Python en tant que Lead Data Engineer"."""
    for phrase in phrases:
        words = _PARENTHESIS.sub(" ", phrase).split()
        if not words:
            continue
        pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in words) + r"(?!\w)"
        for match in reversed(list(re.finditer(pattern, text, flags=re.IGNORECASE))):
            before, after = text[: match.start()], text[match.end() :]
            if _after_employer_word(before) or _cites_posting(before, after):
                text = before + _blank(match) + after
    return text
