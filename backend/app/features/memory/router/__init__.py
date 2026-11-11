"""Routes de la mémoire (14.2), montées sous `/api/v1` : `/memory/...` et `/documents`."""

from fastapi import APIRouter

from app.features.memory.router.documents import router as documents_router
from app.features.memory.router.items import router as items_router

router = APIRouter()
router.include_router(items_router)
router.include_router(documents_router)

__all__ = ["router"]
