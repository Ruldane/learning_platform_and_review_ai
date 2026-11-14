"""Règles pures des offres (D118) : clé d'un lien d'offre, clé d'entreprise, ressemblance de deux
titres, texte suffisant, ATS reconnu par son domaine (`detect_ats`, réexporté de
`app.agents.tools.ats_hosts`, partagé avec le parcours `cv_review`)."""

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

# Paramètres de suivi retirés d'un lien : une entrée finie par « _ » est un préfixe. « ref » et
# « src » n'en sont pas (écart voulu au plan, D118) : des sites carrières y mettent l'offre.
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

PROBABLE_TITLE = 0.85  # même entreprise et titres à 0,85 au moins : doublon probable
POSSIBLE_COSINE = 0.90  # meilleur fragment de mémoire à 0,90 au moins : doublon possible

_NON_ALNUM = re.compile(r"[^0-9a-z+#]+")


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return any(
        lowered.startswith(param) if param.endswith("_") else lowered == param
        for param in TRACKING_PARAMS
    )


def route_fragment(url: str) -> str:
    """Le fragment d'un site à routage par ancre (`#/offre/1`, `#!/offre/1`) : il désigne
    l'offre et reste dans la clé. Tout autre fragment (`#postuler`) est retiré."""
    fragment = urlsplit(url.strip()).fragment
    return fragment if fragment.startswith(("/", "!")) else ""


def posting_url_key(url: str) -> str:
    """La clé d'un lien d'offre : `normalize_url` (lève `invalid_url` ou `url_forbidden`), puis
    « www. » et port par défaut retirés, paramètres de suivi retirés, requête triée, « / »
    final retiré, fragment retiré sauf une route (`route_fragment`). Une clé passée de
    nouveau donne la même clé. Deux offres distinctes ne partagent jamais une clé : un vrai
    doublon manqué ici est rattrapé au niveau « probable » ou « possible »."""
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
