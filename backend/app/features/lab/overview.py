"""La carte de Tremplin et les outils disponibles pour le compte courant."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import MCP_IDENTITY
from app.core.deps import CurrentUserDep, Db, get_providers
from app.core.providers import Providers
from app.features.brain.service import connection
from app.features.calendar.service import connection_status
from app.features.lab.navigation import NAVIGATION
from app.features.settings.keys_service import ApiKeyService
from app.features.settings.service import SettingsService
from app.mcp.base import Level
from app.mcp.registry import Registry

router = APIRouter()
_SECTIONS = {
    "home": ("Accueil", "/"),
    "learn": ("Étudier", "/etudier"),
    "code": ("Coder", "/coder"),
    "memory": ("Cerveau", "/cerveau"),
    "career": ("Carrière", "/carriere"),
    "lab": ("Labo", "/labo"),
    "settings": ("Réglages", "/reglages"),
}
_WITH_MODELS = frozenset(
    {
        "applications",
        "boss",
        "brain",
        "brief",
        "conversations",
        "cv",
        "expert_debates",
        "grade_appeals",
        "ide",
        "learning",
        "lesson_hunt",
        "lessons",
        "linkedin_drafts",
        "oncall",
        "postings",
        "projects",
        "quiz",
        "radar",
        "recruitment_process",
        "research",
        "skill_transfer",
        "study",
        "surprise_interview",
    }
)


class OverviewTool(BaseModel):
    name: str
    level: Level


class OverviewFeature(BaseModel):
    id: str
    tools: list[OverviewTool]
    missing_prerequisites: list[str]


class OverviewSection(BaseModel):
    id: str
    title: str
    local_url: str
    features: list[OverviewFeature]


class Overview(BaseModel):
    sections: list[OverviewSection]


def _tools(registry: Registry) -> dict[str, list[OverviewTool]]:
    identity = MCP_IDENTITY.get()
    available: dict[str, list[OverviewTool]] = defaultdict(list)
    for tool in sorted(registry.all(), key=lambda tool: tool.name):
        if identity is None or tool.available_to(identity):
            available[tool.feature].append(OverviewTool(name=tool.name, level=tool.level))
    return available


async def _missing(
    request: Request, current: CurrentUserDep, db: Db, providers: Providers
) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = defaultdict(list)
    if (await connection(db, current.id)).state != "connected":
        missing["brain"].append("brain_relay")
    if (await connection_status(request.app.state.calendar, db, current.id)).status != "connected":
        missing["calendar"].append("calendar_consent")
    if providers.sandbox is None:
        for feature in ("ide", "code_trial", "oncall"):
            missing[feature].append("sandbox")
    if not await _models_ready(db, current.id, providers):
        for feature in _WITH_MODELS:
            missing[feature].append("models")
    return missing


async def _models_ready(db: AsyncSession, user_id: str, providers: Providers) -> bool:
    settings = await SettingsService(db, user_id).get()
    keys = ApiKeyService(
        db,
        user_id,
        providers.cipher,
        providers.env_keys,
        providers.key_providers,
        llm=providers.llm,
    )
    readable = {key.provider for key in await keys.list() if key.source and key.readable}
    choices = (*settings.tiers.values(), *settings.agent_overrides.values())
    return {choice.provider for choice in choices} <= readable


@router.get("/overview", response_model=Overview)
async def overview(
    request: Request,
    current: CurrentUserDep,
    db: Db,
    providers: Annotated[Providers, Depends(get_providers)],
) -> Overview:
    """Les rubriques, leurs activités, les outils du jeton et les prérequis manquants."""
    available = _tools(request.app.state.mcp_registry)
    missing = await _missing(request, current, db, providers)
    sections: list[OverviewSection] = []
    for key, ids in NAVIGATION.items():
        title, url = _SECTIONS[key]
        features = [
            OverviewFeature(
                id=feature,
                tools=available.get(feature, []),
                missing_prerequisites=missing.get(feature, []),
            )
            for feature in ids
        ]
        sections.append(OverviewSection(id=key, title=title, local_url=url, features=features))
    return Overview(sections=sections)
