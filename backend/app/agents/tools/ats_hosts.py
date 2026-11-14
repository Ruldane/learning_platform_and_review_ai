"""ATS reconnu par le domaine d'un lien (D118, D129) : lien de candidature, lien de l'offre ou page
lue par l'Éclaireur. Règle pure, partagée par la feature `postings` et le parcours `cv_review` (le
moteur n'importe aucune feature, contrat 6)."""

from collections.abc import Iterable
from urllib.parse import urlsplit

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
