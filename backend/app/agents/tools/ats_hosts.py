"""ATS recognized from a link's domain (D118, D129): application link, posting link or page read by
the Scout. Pure rule, shared by the `postings` feature and the `cv_review` flow (the engine imports
no feature, contract 6)."""

from collections.abc import Iterable
from urllib.parse import urlsplit

# Domain (host suffix) -> ATS name.
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
    """The first ATS recognized among the links (host equal to the domain or a subdomain of it)."""
    for url in urls:
        host = _host(url)
        if not host:
            continue
        for domain, name in ATS_HOSTS.items():
            if host == domain or host.endswith(f".{domain}"):
                return name
    return None
