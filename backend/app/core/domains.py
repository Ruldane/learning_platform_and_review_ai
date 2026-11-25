"""Domain name entered in the search settings: a rule shared by the settings validation
(`features.settings`) and the ranking of the results (`features.research`)."""

import re

# Same rule as the front end's `normalizeDomain.ts` (search settings): both must accept
# and refuse exactly the same inputs. `[0-9]` and `fullmatch` so as not to depend on `\d`
# (Unicode digits) or on `$` (which tolerates a trailing line break).
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
_LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_TLD = re.compile(r"[a-z]{2,63}|xn--[a-z0-9-]{1,59}")
_PORT = re.compile(r":[0-9]*\Z")
_MAX_HOST = 253


def normalize_domain(value: str) -> str:
    """Brings an input down to a domain name: lowercase, without scheme, credentials, path,
    query, fragment, port, trailing dot or "www.". Raises `ValueError` if it is not a
    domain: at least two labels, alphabetic extension (IP addresses and "localhost"
    refused)."""
    host = _SCHEME.sub("", value.strip().lower(), count=1)
    host = re.split(r"[/?#]", host, maxsplit=1)[0]
    host = host[host.rfind("@") + 1 :]
    host = _PORT.sub("", host, count=1)
    host = host.removesuffix(".")
    host = host.removeprefix("www.")
    labels = host.split(".")
    if not 0 < len(host) <= _MAX_HOST or len(labels) < 2:
        raise ValueError("invalid domain")
    if not all(_LABEL.fullmatch(label) for label in labels):
        raise ValueError("invalid domain")
    if not _TLD.fullmatch(labels[-1]):
        raise ValueError("invalid domain")
    return host
