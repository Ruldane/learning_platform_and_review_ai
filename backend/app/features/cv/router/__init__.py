"""Routes du CV (14.2), montées sous `/api/v1` : le profil maître (`/profile`), puis les gabarits
et les revues (preflight G16 : un paquet de routeurs, comme `memory`)."""

from fastapi import APIRouter

from app.features.cv.router.profile import router as profile_router

router = APIRouter()
router.include_router(profile_router)

__all__ = ["router"]
