"""Routes du CV (14.2), montées sous `/api/v1` : le profil maître (`/profile`), les gabarits
(`/cv/templates`), puis les revues (preflight G16 : un paquet de routeurs, comme `memory`)."""

from fastapi import APIRouter

from app.features.cv.router.profile import router as profile_router
from app.features.cv.router.templates import router as templates_router

router = APIRouter()
router.include_router(profile_router)
router.include_router(templates_router)

__all__ = ["router"]
