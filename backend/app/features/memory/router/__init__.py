"""Memory routes (14.2), mounted under `/api/v1`: `/memory/...` and `/documents`."""

from fastapi import APIRouter

from app.features.memory.router.documents import router as documents_router
from app.features.memory.router.explorer import router as explorer_router
from app.features.memory.router.items import router as items_router

router = APIRouter()
router.include_router(items_router)
router.include_router(explorer_router)
router.include_router(documents_router)

__all__ = ["router"]
