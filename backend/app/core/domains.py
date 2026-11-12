"""Nom de domaine saisi dans les réglages de recherche : règle partagée par la validation des
réglages (`features.settings`) et le classement des résultats (`features.research`)."""

import re

# Même règle que `normalizeDomain.ts` du front (réglages de recherche) : les deux doivent accepter
# et refuser exactement les mêmes saisies. `[0-9]` et `fullmatch` pour ne pas dépendre de `\d`
# (chiffres Unicode) ni de `$` (qui tolère un saut de ligne final).
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
_LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_TLD = re.compile(r"[a-z]{2,63}|xn--[a-z0-9-]{1,59}")
_PORT = re.compile(r":[0-9]*\Z")
_MAX_HOST = 253


def normalize_domain(value: str) -> str:
    """Ramène une saisie à un nom de domaine : minuscules, sans schéma, identifiants, chemin,
    requête, fragment, port, point final ni « www. ». Lève `ValueError` si ce n'est pas un
    domaine : au moins deux étiquettes, extension alphabétique (adresses IP et « localhost »
    refusées)."""
    host = _SCHEME.sub("", value.strip().lower(), count=1)
    host = re.split(r"[/?#]", host, maxsplit=1)[0]
    host = host[host.rfind("@") + 1 :]
    host = _PORT.sub("", host, count=1)
    host = host.removesuffix(".")
    host = host.removeprefix("www.")
    labels = host.split(".")
    if not 0 < len(host) <= _MAX_HOST or len(labels) < 2:
        raise ValueError("domaine invalide")
    if not all(_LABEL.fullmatch(label) for label in labels):
        raise ValueError("domaine invalide")
    if not _TLD.fullmatch(labels[-1]):
        raise ValueError("domaine invalide")
    return host
