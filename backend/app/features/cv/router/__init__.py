"""Routes du CV (14.2), montées sous `/api/v1` : le profil maître (`/profile`), les gabarits
(`/cv/templates`), les revues et leurs modifications (`/cv/reviews`, `/cv/modifications`) et les
versions produites (`/cv/versions`) (preflight G16 : un paquet de routeurs, comme `memory`)."""

from fastapi import APIRouter

from app.features.cv.router.profile import router as profile_router
from app.features.cv.router.reviews import router as reviews_router
from app.features.cv.router.templates import router as templates_router
from app.features.cv.router.versions import router as versions_router

router = APIRouter()
router.include_router(profile_router)
router.include_router(templates_router)
router.include_router(reviews_router)
router.include_router(versions_router)

__all__ = ["router"]
