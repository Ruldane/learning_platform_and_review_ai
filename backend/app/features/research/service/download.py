"""Copie locale d'un PDF librement téléchargeable (SPEC 3.6, D91) : la ressource d'une leçon
dont l'adresse rend un PDF est gardée sur le disque, sinon elle reste un lien et une fiche de
lecture.

Le téléchargement passe par le fetcher sûr de la recherche (garde SSRF : adresses publiques en
http(s) seulement, chaque redirection revérifiée, 20 Mo au plus, 15 s) et ne demande QUE le type
`application/pdf`. Un domaine exclu dans les réglages n'est jamais contacté. Toute erreur rend
`None` ; journaux : identifiants et code seulement, jamais l'adresse (SPEC 17.2)."""

import logging
from urllib.parse import urlsplit

from app.core.errors import AppError
from app.features.research.service.domains import host_matches
from app.features.research.service.prefs import load_prefs
from app.features.research.service.runtime import ResearchRuntime

logger = logging.getLogger(__name__)

PDF_TYPES = ("application/pdf",)
MAX_PDF_BYTES = 20 * 1024 * 1024
_PDF_MAGIC = b"%PDF-"


async def _excluded(runtime: ResearchRuntime, user_id: str, url: str) -> bool:
    async with runtime.session_factory() as db:
        prefs = await load_prefs(db, user_id)
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return True
    return any(host_matches(host, domain) for domain in prefs.excluded)


async def download_pdf(runtime: ResearchRuntime, user_id: str, url: str) -> bytes | None:
    """Le PDF à `url` (20 Mo au plus, signature `%PDF-` vérifiée), `None` sinon : domaine exclu,
    adresse refusée par la garde, autre type de contenu, page illisible, fichier trop gros."""
    if await _excluded(runtime, user_id, url):
        logger.info("PDF non téléchargé (utilisateur %s) : domaine exclu", user_id)
        return None
    try:
        fetched = await runtime.providers.fetcher.fetch(url, content_types=PDF_TYPES)
    except AppError as exc:
        logger.info("PDF non téléchargé (utilisateur %s) : %s", user_id, exc.code)
        return None
    except Exception as exc:  # message brut jamais journalisé (il pourrait citer l'adresse)
        logger.warning("PDF non téléchargé (utilisateur %s) : %s", user_id, type(exc).__name__)
        return None
    body = fetched.body
    if len(body) > MAX_PDF_BYTES or not body.startswith(_PDF_MAGIC):
        logger.info("PDF non téléchargé (utilisateur %s) : contenu refusé", user_id)
        return None
    return body
