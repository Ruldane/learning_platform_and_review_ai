"""Document `.ipynb` v4. Les champs descriptifs existants restent dans le fichier."""

import json
from typing import Any

from pydantic import ValidationError

from app.core.errors import AppError
from app.features.ide.schemas_notebook import MAX_NOTEBOOK_CELLS, NotebookCellIn, NotebookCellOut

_OUTPUT_LIMIT = 4_000


def invalid() -> AppError:
    return AppError("notebook_invalid", "Le notebook doit contenir des cellules Jupyter v4.", 422)


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(piece, str) for piece in value):
        return "".join(value)
    raise invalid()


def _view(raw: dict[str, Any]) -> NotebookCellOut:
    output: str | None = None
    if raw.get("cell_type") == "code":
        values = raw.get("outputs", [])
        if not isinstance(values, list):
            raise invalid()
        streams = [
            _as_text(item.get("text", ""))
            for item in values
            if isinstance(item, dict) and item.get("output_type") == "stream"
        ]
        if streams:
            output = "".join(streams)[:_OUTPUT_LIMIT]
    try:
        return NotebookCellOut.model_validate(
            {
                "id": raw.get("id"),
                "kind": raw.get("cell_type"),
                "source": _as_text(raw.get("source", "")),
                "output": output,
                "execution_count": raw.get("execution_count"),
            }
        )
    except (ValidationError, TypeError):
        raise invalid() from None


class Notebook:
    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @classmethod
    def parse(cls, text: str) -> "Notebook":
        if not text.strip():
            return cls({"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": []})
        try:
            raw = json.loads(text)
        except (ValueError, RecursionError):
            raise invalid() from None
        cells = raw.get("cells") if isinstance(raw, dict) and raw.get("nbformat") == 4 else None
        if not isinstance(cells, list) or len(cells) > MAX_NOTEBOOK_CELLS:
            raise invalid()
        for index, cell in enumerate(cells):
            if not isinstance(cell, dict):
                raise invalid()
            cell.setdefault("id", f"cell-{index + 1}")
        notebook = cls(raw)
        if len({cell.id for cell in notebook.cells()}) != len(cells):
            raise invalid()
        return notebook

    def cells(self) -> list[NotebookCellOut]:
        return [_view(raw) for raw in self._raw["cells"]]

    def replace(self, cells: list[NotebookCellIn]) -> None:
        if len({cell.id for cell in cells}) != len(cells):
            raise invalid()
        raw_by_id = {raw["id"]: raw for raw in self._raw["cells"]}
        self._raw["cells"] = [_edit(raw_by_id.get(cell.id, {}), cell) for cell in cells]
        self._raw["nbformat_minor"] = 5

    def source(self, cell_id: str, *, include_previous: bool) -> str:
        previous: list[str] = []
        for cell in self.cells():
            if cell.id == cell_id and cell.kind == "code":
                return "\n\n".join([*previous, cell.source])
            if include_previous and cell.kind == "code":
                previous.append(cell.source)
        raise AppError("cell_not_found", "Cellule Python introuvable.", 404)

    def record_output(self, cell_id: str, output: str) -> None:
        raw = next(cell for cell in self._raw["cells"] if cell["id"] == cell_id)
        raw["outputs"] = [
            {"output_type": "stream", "name": "stdout", "text": output[:_OUTPUT_LIMIT]}
        ]
        raw["execution_count"] = (raw.get("execution_count") or 0) + 1

    def to_json(self) -> str:
        return json.dumps(self._raw, ensure_ascii=False, separators=(",", ":"))


def _edit(previous: dict[str, Any], cell: NotebookCellIn) -> dict[str, Any]:
    value = {**previous, "id": cell.id, "cell_type": cell.kind, "source": cell.source}
    value.setdefault("metadata", {})
    if cell.kind != "code":
        value.pop("execution_count", None)
        value.pop("outputs", None)
    elif previous.get("cell_type") != "code" or _as_text(previous.get("source", "")) != cell.source:
        value.update(execution_count=None, outputs=[])
    return value
