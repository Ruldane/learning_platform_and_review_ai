"""Description textuelle des liens Excalidraw, en gardant les id hors du prompt."""

from typing import Any

from app.core.errors import AppError

MAX_ELEMENTS = 120
MAX_DIAGRAM_CHARS = 5500


def _visible(scene: dict[str, Any] | None) -> list[dict[str, Any]]:
    value = (scene or {}).get("elements")
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, dict) and not item.get("isDeleted") and isinstance(item.get("id"), str)
    ][:MAX_ELEMENTS]


def _binding(value: object, names: dict[str, str]) -> str:
    if isinstance(value, dict) and isinstance(element_id := value.get("elementId"), str):
        return names.get(element_id, "hors extrait")
    return "non relié"


def describe_scene(scene: dict[str, Any] | None) -> str:
    elements = _visible(scene)
    if not elements:
        raise AppError("design_board_empty", "Ajoute des éléments au schéma et enregistre-le.", 422)
    names = {item["id"]: f"E{index}" for index, item in enumerate(elements, 1)}
    lines = []
    for item in elements:
        kind = str(item.get("type", ""))[:24]
        name = names[item["id"]]
        parent = item.get("containerId")
        if kind in {"arrow", "line"}:
            start = _binding(item.get("startBinding"), names)
            end = _binding(item.get("endBinding"), names)
            lines.append(f"{name} {kind} : {start} → {end}")
        elif isinstance(parent, str) and parent in names:
            lines.append(f"{name} texte de {names[parent]} : {str(item.get('text', ''))[:220]}")
        else:
            text = str(item.get("text", ""))[:220]
            lines.append(f"{name} {kind} : {text}".rstrip())
    return "\n".join(lines)[:MAX_DIAGRAM_CHARS]
