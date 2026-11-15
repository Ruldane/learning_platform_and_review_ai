"""Ce qu'un texte peut dire sans que ce soit un fait de January (contrôle `text_claims`) : ses
propres coordonnées (téléphone, email, liens du profil), les jours du mois (« le 12 novembre ») et
les expressions citées de l'offre (entreprise, intitulé, contact). Chaque masque remplace le texte
par des espaces de même longueur : les positions des autres termes ne bougent pas."""

import re
from collections.abc import Sequence

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import normalize_term

# Un mot de l'offre ou de l'employeur juste avant une expression : elle est citée, pas revendiquée.
CITING_WORDS = frozenset(
    """poste offre role candidature opportunite position opening job chez at pour for avec with
    rejoindre rejoint join joined joining aupres""".split()  # noqa: SIM905
)
_MIN_PHONE_DIGITS = 6
CITING_WINDOW = 6  # mots avant l'expression, dans la même proposition
_CLAUSE_BREAK = re.compile(r"[.,;!?\n]")
_MONTHS = (
    "janvier février fevrier mars avril mai juin juillet août aout septembre octobre novembre "
    "décembre decembre january february march april may june july august september october "
    "november december"
).replace(" ", "|")
_DAY_MONTH = re.compile(
    rf"(?<!\w)\d{{1,2}}(?:er|st|nd|rd|th)?\s+(?:(?:de|of)\s+)?(?:{_MONTHS})(?!\w)", re.IGNORECASE
)
_MONTH_DAY = re.compile(rf"(?<!\w)(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?!\d)", re.IGNORECASE)
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


def _cited(before: str) -> bool:
    """Un mot de l'offre ou de l'employeur figure parmi les mots qui précèdent, sans saut de
    proposition."""
    clause = _CLAUSE_BREAK.split(before)[-1]
    words = normalize_term(clause).split()[-CITING_WINDOW:]
    return any(word in CITING_WORDS for word in words)


def mask_phrases(text: str, phrases: Sequence[str], *, cited_only: bool) -> str:
    """Retire du texte, là où elles figurent, les expressions entières de `phrases` (entreprise,
    intitulé exact de l'offre, nom d'un contact ; sans la parenthèse « (H/F) »). Avec
    `cited_only`, une expression n'est retirée que précédée d'un mot de l'offre ou de l'employeur
    (« votre poste de Développeuse IA », « chez Société Fictive ») : « en tant que Lead Data »
    reste lu."""
    for phrase in phrases:
        words = _PARENTHESIS.sub(" ", phrase).split()
        if not words:
            continue
        pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in words) + r"(?!\w)"
        for match in reversed(list(re.finditer(pattern, text, flags=re.IGNORECASE))):
            if not cited_only or _cited(text[: match.start()]):
                text = text[: match.start()] + _blank(match) + text[match.end() :]
    return text
