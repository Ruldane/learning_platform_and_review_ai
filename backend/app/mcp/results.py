"""Ce que l'envoyeur fait d'une réponse de route (phase 10, P12, P13) : lire le corps, filtrer les
champs (`response_fields`), rendre une 422 lisible avec les noms d'arguments de l'outil, extraire
les identifiants pour le journal, et poster un formulaire sans fichier."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import Message
from typing import Any

import httpx

from app.mcp.arguments import clip
from app.mcp.envelope import fence
from app.mcp.tools import ToolResult, ToolSpec


def form_fields(body: Any) -> list[tuple[str, tuple[None, str]]]:
    """Les champs texte d'un formulaire : `multipart/form-data` sans aucun fichier."""
    fields: list[tuple[str, tuple[None, str]]] = []
    for key, value in (body or {}).items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if item is None:
                continue
            if isinstance(item, bool):
                text = "true" if item else "false"
            elif isinstance(item, dict):
                text = json.dumps(item, ensure_ascii=False)
            else:
                text = str(item)
            fields.append((key, (None, text)))
    return fields


def read_response(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if response.status_code == 204 or not response.content:
        return None
    if "json" in content_type:
        try:
            return response.json()
        except ValueError:
            return {"content_type": content_type.split(";")[0], "size": len(response.content)}
    return {"content_type": content_type.split(";")[0], "size": len(response.content)}


_TEXT_MEDIA = {"application/json", "text/calendar", "text/markdown", "text/plain"}
_FILE_TEXT_BYTES = 30_000


def artifact_response(response: httpx.Response, local_url: str | None) -> dict[str, Any]:
    """Métadonnées et texte disponible sans diffuser le contenu binaire ni une redirection."""
    media = response.headers.get("content-type", "").split(";")[0]
    disposition = Message()
    disposition["Content-Disposition"] = response.headers.get("content-disposition", "")
    metadata: dict[str, Any] = {"content_type": media}
    if local_url:
        metadata["local_url"] = local_url
    if filename := disposition.get_filename():
        metadata["filename"] = clip(filename.replace("\\", "/").rsplit("/", 1)[-1], 180)
    if response.content:
        metadata["size"] = len(response.content)
    if media in _TEXT_MEDIA:
        metadata["text"] = response.content[:_FILE_TEXT_BYTES].decode("utf-8", errors="replace")
        metadata["truncated"] = len(response.content) > _FILE_TEXT_BYTES
    return metadata


def filter_fields(data: Any, fields: frozenset[str] | None) -> Any:
    """`response_fields` : seules ces clés de l'objet racine (de chaque objet d'une liste)."""
    if fields is None:
        return data
    if isinstance(data, dict):
        return {key: value for key, value in data.items() if key in fields}
    if isinstance(data, list):
        return [filter_fields(item, fields) for item in data]
    return data


def fence_sessions(data: Any, paths: Mapping[str, tuple[str, ...]]) -> Any:
    """Entoure les résultats des graphes qui lisent des sources non fiables."""
    if isinstance(data, list):
        return [fence_sessions(item, paths) for item in data]
    if isinstance(data, dict) and isinstance(data.get("graph"), str) and data["graph"] in paths:
        return fence(data, paths[data["graph"]])
    return data


def translate_validation(data: Any, tool: ToolSpec) -> Any:
    """Une 422 de validation de la route, lisible avec les noms d'arguments de l'outil, sans
    jamais la valeur reçue : `details.errors` (seuls `loc`, `msg` et `type` sont repris) ou
    `details.fields` (chemins de champs des routes à champs nommés). Toute autre 422 (une règle
    de la feature) passe telle quelle."""
    details = (data or {}).get("error", {}).get("details") if isinstance(data, dict) else None
    if not isinstance(details, dict):
        return data
    inverse = {key: arg for arg, key in (tool.plan.body_args.items() if tool.plan else ())}
    readable: list[dict[str, str]] = []
    if isinstance(details.get("errors"), list):
        for err in details["errors"][:20]:
            parts = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            readable.append(
                {
                    "field": field_path(parts, inverse),
                    "message": clip(err.get("msg", ""), 160),
                    "type": clip(err.get("type", ""), 40),
                }
            )
    elif isinstance(details.get("fields"), list):
        for path in details["fields"][:20]:
            readable.append({"field": field_path(str(path).split("."), inverse)})
    else:
        return data
    listed = " ; ".join(
        f"{e['field']} ({e['message']})" if "message" in e else e["field"] for e in readable[:5]
    )
    return {
        "error": {
            "code": "validation_error",
            "message": f"Arguments invalides : {listed}",
            "details": {"errors": readable},
        }
    }


def field_path(parts: list[str], inverse: Mapping[str, str]) -> str:
    """Le chemin d'un champ en erreur, son premier segment renommé en argument de l'outil."""
    first = inverse.get(parts[0], parts[0]) if parts else "?"
    return clip(".".join([first, *parts[1:]]), 80)


_RESOURCE_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[45][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_UNVERIFIED_IDS = frozenset({"ref_id", "request_id", "source_id", "subject_id"})
_CREATED_RESOURCES = ("application", "goal", "posting")


def result_ids(data: Any) -> dict[str, str]:
    """Identifiants Tremplin d'une réponse réussie, UUID4 ou UUID5 pour les conversations.

    Les références libres et les clés d'idempotence peuvent venir de la saisie. Les sous-objets
    des réponses de création nommées portent l'identifiant de la ressource créée.
    """
    if not isinstance(data, dict):
        return {}
    ids = {
        key: value
        for key, value in data.items()
        if (key == "id" or key.endswith("_id"))
        and key not in _UNVERIFIED_IDS
        and isinstance(value, str)
        and _RESOURCE_ID.fullmatch(value)
    }
    for resource in _CREATED_RESOURCES:
        created = data.get(resource)
        resource_id = created.get("id") if isinstance(created, dict) else None
        if isinstance(resource_id, str) and _RESOURCE_ID.fullmatch(resource_id):
            ids[f"{resource}_id"] = resource_id
    return ids


def timed_out(data: Any, call_id: str | None) -> ToolResult:
    """Délai dépassé sur une écriture : la route a pu valider ses écritures avant de répondre.
    Claude le lit (`notice`) avant de relancer, le journal le garde (`outcome: timeout`) ; rien
    n'a été enregistré pour l'annulation."""
    notice = (
        "La route a pu écrire avant le délai : vérifie l'état (lecture) avant de relancer, "
        "et cet appel ne pourra pas être annulé depuis l'application."
    )
    return ToolResult(
        data=data,
        code=504,
        ids={"outcome": "timeout"},
        call_id=call_id,
        notice=notice,
    )


@dataclass(frozen=True)
class InternalResponse:
    """La réponse de la route : code HTTP et corps (JSON lu, `None` si vide)."""

    status: int
    data: Any


def internal_error(status: int, code: str, message: str, details: Any = None) -> InternalResponse:
    return InternalResponse(
        status, {"error": {"code": code, "message": message, "details": details}}
    )
