"""Ce que l'envoyeur fait d'une réponse de route (phase 10, P12, P13) : lire le corps, filtrer les
champs (`response_fields`), rendre une 422 lisible avec les noms d'arguments de l'outil, extraire
les identifiants pour le journal, et poster un formulaire sans fichier."""

import json
from collections.abc import Mapping
from typing import Any

import httpx

from app.mcp.arguments import clip
from app.mcp.tools import ToolSpec


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


def filter_fields(data: Any, fields: frozenset[str] | None) -> Any:
    """`response_fields` : seules ces clés de l'objet racine (de chaque objet d'une liste)."""
    if fields is None:
        return data
    if isinstance(data, dict):
        return {key: value for key, value in data.items() if key in fields}
    if isinstance(data, list):
        return [filter_fields(item, fields) for item in data]
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


def result_ids(arguments: Mapping[str, Any], data: Any) -> dict[str, Any]:
    """Les identifiants touchés (arguments et réponse) pour le journal ; le journal les filtre."""
    ids: dict[str, Any] = {
        key: value for key, value in arguments.items() if key == "id" or key.endswith("_id")
    }
    if isinstance(data, dict):
        for key, value in data.items():
            if (key == "id" or key.endswith("_id")) and isinstance(value, str | int):
                ids.setdefault(key, value)
    return ids
