"""Ce qu'un texte peut dire sans que ce soit un fait de January (contrôle `text_claims`) : ses
propres coordonnées (téléphone, email, liens du profil), les jours du mois (« le 12 novembre ») et
les expressions citées de l'offre (entreprise, intitulé, contact). Chaque masque remplace le texte
par des espaces de même longueur : les positions des autres termes ne bougent pas."""

import re
from collections.abc import Sequence

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import normalize_term

# Mots qui désignent l'offre : « votre poste de X », « the X position ».
POSTING_WORDS = frozenset(
    "poste offre role candidature opportunite position opening job".split()  # noqa: SIM905
)
# Ce qui précède un mot de l'offre quand il parle de l'offre de l'autre, pas du poste de January.
DETERMINERS = frozenset("votre vos ce cette le la l your this the".split())  # noqa: SIM905
# Un mot qui précède un nom d'entreprise ou de contact : « chez X », « at X », « avec X ».
EMPLOYER_WORDS = frozenset(
    """chez at pour for avec with rejoindre rejoint join joined joining aupres bonjour hello dear
    madame monsieur""".split()  # noqa: SIM905
)
# Mots qui rattachent ce qui suit à January : l'expression n'est plus celle de l'offre.
SELF_WORDS = frozenset(
    """mon ma mes my actuel actuelle current precedent precedente previous j je i""".split()  # noqa: SIM905
)
# Le texte se donne un titre (mots normalisés) : « en tant que », « je suis », « j'étais »…
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
CITING_WINDOW = 6  # mots avant l'expression, dans la même proposition
_CLAUSE_BREAK = re.compile(r"[.,;!?\n]")
_FRENCH_MONTHS = "janvier février fevrier mars avril mai juin juillet août aout septembre octobre"
_FRENCH_MONTHS += " novembre décembre decembre"
# « may » minuscule est le verbe : seul « May » est un mois.
_ENGLISH_MONTHS = (
    "january|february|march|april|(?-i:May)|june|july|august|september|october|november|december"
)
_MONTHS = f"{_FRENCH_MONTHS.replace(' ', '|')}|{_ENGLISH_MONTHS}"
_DAY_MONTH = re.compile(
    rf"(?<!\w)\d{{1,2}}(?:er|st|nd|rd|th)?\s+(?:(?:de|of)\s+)?(?:{_MONTHS})(?!\w)", re.IGNORECASE
)
# « November 12, 2026 », « March 5th », « May 3. » : un nombre suivi d'un nom (« March 5 clients »)
# est un compte, pas un jour.
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
    """Les jours du mois sont masqués (« 12 novembre », « November 12 », « 12/11/ ») : une date
    n'est pas un chiffre du profil. Une année reste : elle se compare aux dates du profil."""
    text = _DAY_MONTH.sub(_blank, text)
    text = _MONTH_DAY.sub(_blank, text)
    return _NUMERIC_DATE.sub(lambda m: " " * len(m.group(1)) + m.group(2), text)


def _literal(value: str, *, phone: bool = False) -> str:
    """Le motif d'une coordonnée écrite telle quelle : un numéro de téléphone se lit avec
    n'importe quels séparateurs (espaces, points, tirets) entre ses chiffres."""
    if phone:
        digits = re.sub(r"\D", "", value)
        return r"[\s.\-]?".join(digits) if len(digits) >= _MIN_PHONE_DIGITS else ""
    link = re.sub(r"^\w+://", "", value.strip()).rstrip("/")
    return re.escape(link) if link else ""


def mask_own_contacts(text: str, profile: MasterProfileData) -> str:
    """Le téléphone, l'email et les liens du profil, écrits dans le texte (signature), sont
    masqués : leurs chiffres ne sont jamais une référence."""
    patterns = [_literal(profile.identity.phone or "", phone=True)]
    patterns.append(_literal(profile.identity.email or ""))
    patterns += [_literal(link.url) for link in profile.links]
    patterns += [_literal(project.link or "") for project in profile.projects]
    for pattern in filter(None, patterns):
        text = re.sub(rf"(?<!\w)(?:\w+://)?{pattern}/?", _blank, text, flags=re.IGNORECASE)
    return text


def _has_cue(words: Sequence[str]) -> bool:
    """Une formule d'attribution (`SELF_CUES`) figure parmi `words`."""
    return any(
        tuple(words[rank : rank + len(cue)]) == cue
        for cue in SELF_CUES
        for rank in range(len(words))
    )


def _cites_posting(before: str, after: str) -> bool:
    """L'expression parle de l'offre : « votre poste de X » (un mot de l'offre, précédé de
    « votre », « le »…, dans les 6 mots d'avant, sans « mon », « actuel », « je » ni formule
    d'attribution entre le mot de l'offre et l'expression) ou « the X role » (un déterminant
    avant, un mot de l'offre juste après)."""
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
    """Retire du texte, là où elles figurent, les expressions entières de `phrases` (entreprise,
    intitulé exact de l'offre, nom d'un contact ; sans la parenthèse « (H/F) »), mais seulement
    quand le texte les cite : juste après « chez », « at », « avec »… (une entreprise, un
    contact) ou comme l'offre de l'autre (`_cites_posting`). Ailleurs elles restent lues :
    « en tant que Lead Data », « Je travaille avec Python en tant que Lead Data Engineer »."""
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
