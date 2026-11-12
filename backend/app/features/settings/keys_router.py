from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.deps import CurrentUserDep, Db, get_providers
from app.core.providers import Providers
from app.features.settings.keys_schemas import ApiKeyIn, ApiKeyOut, ModelsOut
from app.features.settings.keys_service import ApiKeyService
from app.providers.llm.base import KeyTestResult

router = APIRouter(prefix="/settings", tags=["settings"])

ProvidersDep = Annotated[Providers, Depends(get_providers)]


def _service(db: Db, current: CurrentUserDep, providers: ProvidersDep) -> ApiKeyService:
    return ApiKeyService(
        db,
        current.id,
        providers.cipher,
        providers.env_keys,
        providers.key_providers,
        llm=providers.llm,
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    current: CurrentUserDep, db: Db, providers: ProvidersDep
) -> list[ApiKeyOut]:
    return await _service(db, current, providers).list()


@router.post("/api-keys", response_model=ApiKeyOut)
async def save_api_key(
    body: ApiKeyIn, current: CurrentUserDep, db: Db, providers: ProvidersDep
) -> ApiKeyOut:
    return await _service(db, current, providers).set(body.provider, body.key.get_secret_value())


@router.delete("/api-keys/{provider}", status_code=204)
async def delete_api_key(
    provider: str, current: CurrentUserDep, db: Db, providers: ProvidersDep
) -> Response:
    await _service(db, current, providers).delete(provider)
    return Response(status_code=204)


@router.post("/api-keys/{provider}/test", response_model=KeyTestResult)
async def test_api_key(
    provider: str, current: CurrentUserDep, db: Db, providers: ProvidersDep
) -> KeyTestResult:
    return await _service(db, current, providers).test(provider)


@router.get("/models", response_model=ModelsOut)
async def list_models(current: CurrentUserDep, db: Db, providers: ProvidersDep) -> ModelsOut:
    return await _service(db, current, providers).models_overview()
