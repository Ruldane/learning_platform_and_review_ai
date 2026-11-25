from typing import Any

from fastapi import FastAPI

from app.agents.runtime.events import SESSION_EVENT_ADAPTER


def register_event_schemas(app: FastAPI) -> None:
    """Adds `SessionEvent` and its variants to the OpenAPI `components.schemas`.

    The WebSocket does not appear in the OpenAPI: this is how the front end receives the types of
    events (D10). The "serialization" mode makes mandatory the fields that have a default value,
    since the server always sends them.
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
