"""Schémas du radar du marché (P5, P6) : les requêtes de recherche, construites par le code (aucun
modèle n'écrit une requête), et la sortie de l'Analyste, une extraction par lot de cinq offres.

Rien ici n'invente une donnée : les requêtes ne contiennent que le poste, la zone et des sites
d'offres publics ; l'extraction est contrôlée par le code (`analyst_radar`) avant d'être rangée."""

import re
from collections.abc import Sequence
from typing import Literal, NamedTuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field

# Pages d'offres publiques (SPEC 10) : une requête ciblée par site.
SITE_HINTS = (
    "jobs.lever.co",
    "boards.greenhouse.io",
    "welcometothejungle.com",
    "jobs.ashbyhq.com",
)
MAX_QUERIES = 6  # plafond de session : 12 requêtes
BATCH = 5  # offres par appel de l'Analyste (10 appels au plus pour 50 offres)
TEXT_MAX = 4000  # caractères d'une offre montrés à l'Analyste
READ_BATCH = 10  # liens lus par passage de la boucle de lecture
READ_PARALLEL = 5  # lectures simultanées
TIME_RANGE = "month"  # fenêtre de la recherche : les offres du mois

type Level = Literal["junior", "confirme", "senior", "lead", "inconnu"]


class RadarSearch(NamedTuple):
    """Une requête du radar et la langue des résultats attendus (`None` : sans préférence)."""

    query: str
    lang: str | None


_DIGITS = re.compile(r"\d+")


def salary_in_text(salary: str | None, text: str) -> str | None:
    """Le salaire relevé par le modèle, gardé seulement si chacun de ses nombres figure dans le
    texte de l'offre (nombre entier de chiffres : 45 n'est pas 450). Même règle que
    `radar.service.rules.salary_shown` (le moteur n'importe pas la feature ; un test vérifie
    l'accord). Un salaire vide ou sans chiffre : `None`."""
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
    """La clé d'un lien d'offre pour dédoublonner les résultats et suivre les lectures : la même
    que `postings.service.rules.posting_url_key` (le moteur n'importe pas la feature ; un test
    vérifie l'accord sur une table de liens). `None` : lien invalide (autre schéma, sans hôte,
    avec identifiants) ; il n'est jamais lu."""
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


def radar_searches(role: str, zone: str, languages: Sequence[str]) -> list[RadarSearch]:
    """Les requêtes du relevé : en français « offre d'emploi {poste} {zone} » et « {poste} {zone}
    recrutement CDI », pour toute autre langue « {poste} job {zone} », puis « {poste} {zone}
    site:{site} » pour chaque site d'offres. Sans doublon, `MAX_QUERIES` au plus (les dernières
    requêtes ciblées sont laissées si les langues en prennent la place). Sans poste : aucune."""
    role, zone = _clean(role), _clean(zone)
    if not role:
        return []
    where = f" {zone}" if zone else ""
    langs = [lang for lang in dict.fromkeys(languages) if lang] or ["fr"]
    found: list[RadarSearch] = []
    for lang in langs:
        if lang == "fr":
            found.append(RadarSearch(f"offre d'emploi {role}{where}", lang))
            found.append(RadarSearch(f"{role}{where} recrutement CDI", lang))
        else:
            found.append(RadarSearch(f"{role} job{where}", lang))
    found += [RadarSearch(f"{role}{where} site:{hint}", langs[0]) for hint in SITE_HINTS]
    seen: set[str] = set()
    unique: list[RadarSearch] = []
    for search in found:
        if search.query not in seen:
            seen.add(search.query)
            unique.append(search)
    return unique[:MAX_QUERIES]


def radar_queries(role: str, zone: str, languages: Sequence[str]) -> list[str]:
    """Le texte des requêtes de `radar_searches`."""
    return [search.query for search in radar_searches(role, zone, languages)]


class SkillNeedLite(BaseModel):
    """Une compétence demandée par l'offre ; `required` : exigée plutôt que souhaitée."""

    name: str = Field(min_length=2, max_length=80)
    required: bool


class RadarItem(BaseModel):
    """L'extraction d'une offre. `ref` : le repère de l'offre dans le lot (`p1` à `p5`) ; le port
    la reçoit réécrite avec le repère de la page (`PostingPage.ref`). `is_job_posting` faux : la
    page n'est pas une offre, le reste est ignoré."""

    ref: str = Field(pattern=r"^p[1-5]$")
    is_job_posting: bool
    title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: Level = "inconnu"
    remote: str | None = Field(default=None, max_length=60)
    salary: str | None = Field(default=None, max_length=80)
    skills: list[SkillNeedLite] = Field(default_factory=list, max_length=15)
    tools: list[str] = Field(default_factory=list, max_length=15)


class RadarBatch(BaseModel):
    items: list[RadarItem] = Field(max_length=BATCH)


class RadarFinding(RadarItem):
    """L'extraction d'une offre rangée sous le repère de sa **page** (`PostingPage.ref` : `p1`,
    `p12`, `r1`…), pas sous le repère du lot de cinq (`RadarItem.ref`, `p1` à `p5`). C'est ce que
    le port reçoit : `ref` y est libre (1 à 16 caractères), si bien qu'une relecture de
    validation, ici ou dans l'adaptateur, n'échoue jamais sur un repère de page."""

    ref: str = Field(min_length=1, max_length=16)
