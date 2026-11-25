"""CV routes (14.2), mounted under `/api/v1`: the master profile (`/profile`), the templates
(`/cv/templates`), the reviews and their modifications (`/cv/reviews`, `/cv/modifications`) and
the produced versions (`/cv/versions`) (preflight G16: a package of routers, like `memory`)."""

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
