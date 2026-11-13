"""Règles pures des offres (D118) : clé d'un lien d'offre, clé d'entreprise, ressemblance de deux
titres, texte suffisant, ATS reconnu par son domaine."""

import re
from collections.abc import Iterable
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.skills import normalize_skill_name
from app.features.memory.service.upload import normalize_url

# Paramètres de suivi retirés d'un lien : une entrée finie par « _ » est un préfixe.
TRACKING_PARAMS = ("utm_", "gclid", "fbclid", "mc_cid", "mc_eid", "trk", "ref", "src")
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

PROBABLE_TITLE = 0.85  # même entreprise et titres à 0,85 au moins : doublon probable
POSSIBLE_COSINE = 0.90  # meilleur fragment de mémoire à 0,90 au moins : doublon possible
MIN_POSTING_CHARS = 300
MIN_POSTING_WORDS = 50

# Domaine (suffixe d'hôte) → nom de l'ATS.
ATS_HOSTS: dict[str, str] = {
    "greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "myworkdayjobs.com": "Workday",
    "smartrecruiters.com": "SmartRecruiters",
    "teamtailor.com": "Teamtailor",
    "ashbyhq.com": "Ashby",
    "recruitee.com": "Recruitee",
    "workable.com": "Workable",
    "welcometothejungle.com": "Welcome to the Jungle",
    "taleo.net": "Taleo",
    "icims.com": "iCIMS",
    "jobvite.com": "Jobvite",
    "bamboohr.com": "BambooHR",
    "successfactors.com": "SAP SuccessFactors",
    "successfactors.eu": "SAP SuccessFactors",
}

_NON_ALNUM = re.compile(r"[^0-9a-z+#]+")


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return any(
        lowered.startswith(param) if param.endswith("_") else lowered == param
        for param in TRACKING_PARAMS
    )


def posting_url_key(url: str) -> str:
    """La clé d'un lien d'offre : `normalize_url` (lève `invalid_url` ou `url_forbidden`), puis
    « www. » retiré, paramètres de suivi retirés, requête triée, « / » final retiré. Une clé
    passée de nouveau donne la même clé."""
    parts = urlsplit(normalize_url(url))
    netloc = parts.netloc.removeprefix("www.")
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(key)
    )
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, netloc, path, urlencode(query), ""))


def _words(text: str) -> list[str]:
    """Mots d'un nom : `normalize_skill_name`, points retirés (« S.A.S. »), puis ponctuation."""
    return _NON_ALNUM.sub(" ", normalize_skill_name(text).replace(".", "")).split()


def company_key(name: str) -> str:
    """La clé d'une entreprise : sans accents ni casse ni ponctuation, formes juridiques finales
    retirées (« Société Fictive SAS » → « societe fictive »). Un nom fait de formes juridiques
    seulement les garde."""
    words = _words(name)
    end = len(words)
    while end > 1 and words[end - 1] in LEGAL_SUFFIXES:
        end -= 1
    return " ".join(words[:end])


def title_similarity(a: str, b: str) -> float:
    """Ressemblance (0..1) de deux titres normalisés, mots triés (« AI Product Engineer » et
    « Product Engineer AI » : 1). Un titre vide ne ressemble à rien."""
    left, right = " ".join(sorted(_words(a))), " ".join(sorted(_words(b)))
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def enough_text(text: str) -> bool:
    """Assez de texte pour une offre : 300 caractères et 50 mots au moins."""
    stripped = text.strip()
    return len(stripped) >= MIN_POSTING_CHARS and len(stripped.split()) >= MIN_POSTING_WORDS


def _host(url: str) -> str | None:
    try:
        return urlsplit(url.strip()).hostname
    except ValueError:
        return None


def detect_ats(urls: Iterable[str]) -> str | None:
    """Le premier ATS reconnu parmi les liens (hôte égal au domaine ou sous-domaine de lui)."""
    for url in urls:
        host = _host(url)
        if not host:
            continue
        for domain, name in ATS_HOSTS.items():
            if host == domain or host.endswith(f".{domain}"):
                return name
    return None
