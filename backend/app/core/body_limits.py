"""Taille des corps des imports, bornée avant toute analyse (413) : un middleware par chemin
d'import. Sorti de `app.main` (D139) pour qu'il reste court."""

from fastapi import FastAPI

from app.core.limits import BodySizeLimit
from app.features.cv.service.profile_import import MAX_PROFILE_FILE_BYTES, TOO_LARGE_MESSAGE
from app.features.memory.service.upload import MAX_UPLOAD_BYTES

# Corps d'un import : le fichier (20 Mo) plus l'enveloppe multipart et les autres champs.
_UPLOAD_BODY_MAX = MAX_UPLOAD_BYTES + 1024 * 1024
# Corps d'une retouche du tableau : scène Excalidraw complète (`serializeAsJSON`, `files` peut
# porter une image) et sa note (D87).
BOARD_BODY_MAX = 2 * 1024 * 1024
# Import du profil maître : CV et LinkedIn (10 Mo chacun), la note et l'enveloppe (D124).
PROFILE_IMPORT_BODY_MAX = 2 * MAX_PROFILE_FILE_BYTES + 1024 * 1024
TEMPLATE_BODY_MAX = MAX_PROFILE_FILE_BYTES + 1024 * 1024  # gabarit : le CV et son nom
# Rendu d'un projet : cinq captures de 5 Mo, la description, le lien et l'enveloppe (D166).
PROJECT_BODY_MAX = 5 * 5 * 1024 * 1024 + 1024 * 1024


def add_body_limits(app: FastAPI, prefix: str) -> None:
    """Taille des corps des imports, bornée avant toute analyse (413) ; `prefix` : celui des
    routes de l'API."""
    app.add_middleware(BodySizeLimit, path=f"{prefix}/documents", max_bytes=_UPLOAD_BODY_MAX)
    app.add_middleware(
        BodySizeLimit, path=f"{prefix}/brain/sync/folders", max_bytes=_UPLOAD_BODY_MAX
    )
    app.add_middleware(BodySizeLimit, path=f"{prefix}/oncall/incidents", max_bytes=64 * 1024)
    app.add_middleware(BodySizeLimit, path=f"{prefix}/mcp/relay", max_bytes=1024)
    app.add_middleware(BodySizeLimit, path=f"{prefix}/ide/terminals", max_bytes=32 * 1024)
    app.add_middleware(BodySizeLimit, path=f"{prefix}/ide/sessions", max_bytes=1_500_000)
    app.add_middleware(  # CV et LinkedIn, 10 Mo chacun (D124)
        BodySizeLimit,
        path=f"{prefix}/profile/import",
        max_bytes=PROFILE_IMPORT_BODY_MAX,
        message=TOO_LARGE_MESSAGE,
    )
    app.add_middleware(  # CV d'origine d'un gabarit, 10 Mo (D126)
        BodySizeLimit,
        path=f"{prefix}/cv/templates",
        max_bytes=TEMPLATE_BODY_MAX,
        message=TOO_LARGE_MESSAGE,
    )
    app.add_middleware(
        BodySizeLimit,
        path=f"{prefix}/boards",
        max_bytes=BOARD_BODY_MAX,
        code="board_too_large",
        message="Tableau trop volumineux : 2 Mio au maximum.",
    )
    app.add_middleware(  # captures d'un rendu de projet : 5 × 5 Mo (D166)
        BodySizeLimit,
        path=f"{prefix}/projects",
        max_bytes=PROJECT_BODY_MAX,
        message="Rendu trop volumineux : 5 captures de 5 Mo au maximum.",
    )
