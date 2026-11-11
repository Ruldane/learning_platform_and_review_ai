from typing import Any

from fastapi import FastAPI

from app.agents.runtime.events import SESSION_EVENT_ADAPTER


def register_event_schemas(app: FastAPI) -> None:
    """Ajoute `SessionEvent` et ses variantes à `components.schemas` de l'OpenAPI.

    Le WebSocket n'apparaît pas dans l'OpenAPI : c'est ainsi que le front reçoit les types des
    événements (D10). Le mode « serialization » rend obligatoires les champs ayant une valeur par
    défaut, car le serveur les envoie toujours.
    """
    original = app.openapi

    def openapi_with_events() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = original()
        event_schema = SESSION_EVENT_ADAPTER.json_schema(
            ref_template="#/components/schemas/{model}", mode="serialization"
        )
        definitions = event_schema.pop("$defs", {})
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas.update(definitions)
        schemas["SessionEvent"] = event_schema
        return schema

    app.openapi = openapi_with_events  # type: ignore[method-assign]
