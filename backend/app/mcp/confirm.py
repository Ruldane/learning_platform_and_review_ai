"""Les demandes « À confirmer » vues de l'adaptateur (phase 10, P15) : la requête gardée telle
qu'elle partirait, son résumé neutre, l'aperçu complet que January lit avant de confirmer
(`preview_fields`) et le port que l'envoyeur utilise pour la ranger. La vie de la demande (état,
expiration, confirmation, refus) est dans `features/mcp/service/confirmations.py`."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol

from app.core.caller import McpIdentity
from app.mcp.arguments import ToolRequest, clip
from app.mcp.envelope import scrub_text
from app.mcp.tools import ToolSpec

CONFIRMATION_TTL = timedelta(hours=24)
MAX_PENDING_PER_TOKEN = 20
_PREVIEW = 60
_PREVIEW_FIELDS = 6
FIELD_PREVIEW_MAX = 500  # caractères montrés par champ
TOTAL_PREVIEW_MAX = 4_000  # caractères montrés pour toute la requête


@dataclass(frozen=True)
class StoredRequest:
    """Ce qui est gardé d'une demande : l'outil, la requête complète (méthode, chemin, paramètres,
    corps) et l'identité qui l'a faite (étiquette, features, mode du jeton). Le compte et le jeton
    sont dans la ligne de la demande, pas ici."""

    tool: str
    request: ToolRequest
    label: str
    features: tuple[str, ...]
    mode: str
    route: str | None = None  # le gabarit de la route (`/applications/{application_id}`)
    target_label: str | None = None  # le libellé lisible de la cible, lu à la création

    def to_json(self) -> dict[str, Any]:
        request = self.request
        return {
            "tool": self.tool,
            "method": request.method,
            "path": request.path,
            "params": request.params,
            "body": request.body,
            "form": request.form,
            "merge_path": request.merge_path,
            "merge_fields": list(request.merge_fields) if request.merge_fields else None,
            "route": self.route,
            "target_label": self.target_label,
            "identity": {"label": self.label, "features": list(self.features), "mode": self.mode},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StoredRequest":
        who = data["identity"]
        fields = data.get("merge_fields")
        request = ToolRequest(
            method=data["method"],
            path=data["path"],
            params=dict(data.get("params") or {}),
            body=data.get("body"),
            form=bool(data.get("form")),
            merge_path=data.get("merge_path"),
            merge_fields=tuple(fields) if fields else None,
        )
        return cls(
            data["tool"],
            request,
            who["label"],
            tuple(who["features"]),
            who["mode"],
            data.get("route"),
            data.get("target_label"),
        )

    def identity(self, user_id: str, token_id: str) -> McpIdentity:
        """L'identité sous laquelle la demande s'exécute : celle enregistrée à la création."""
        mode: Literal["read", "write"] = "write" if self.mode == "write" else "read"
        return McpIdentity(
            user_id=user_id,
            token_id=token_id,
            label=self.label,
            features=frozenset(self.features),
            mode=mode,
        )


class Pending(Protocol):
    """Ce que l'envoyeur lit d'une demande créée."""

    @property
    def id(self) -> str: ...

    @property
    def expires_at(self) -> datetime: ...


class ConfirmationPort(Protocol):
    """Le rangement d'une demande (fourni par la feature `mcp`, pour un compte donné). Lève
    `AppError` 429 `too_many_pending` à 20 demandes en attente pour le jeton."""

    async def ensure_room(self, identity: McpIdentity) -> None:
        """Lève `AppError` 429 `too_many_pending` si le jeton a déjà 20 demandes en attente (à
        tester avant le contrôle préalable, qui peut coûter un appel au modèle)."""
        ...

    async def create(
        self,
        identity: McpIdentity,
        stored: StoredRequest,
        summary: str,
        precheck: dict[str, Any] | None,
    ) -> Pending: ...


def _render(value: Any) -> str:
    """Une valeur en texte : tel quel pour un texte, JSON compact sinon (objets, listes…)."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def preview_fields(request: ToolRequest) -> tuple[list[tuple[str, str]], bool]:
    """**Tous** les champs de la requête (paramètres puis corps), chacun rendu en texte, les clés
    masquées avant la coupe (une clé coupée en deux ne reste jamais lisible), 500 caractères par
    champ et 4 000 en tout. Rend `(champs, tronqué)` ; un champ coupé finit par « … », un champ
    au-delà du total est nommé avec un aperçu vide."""
    items: list[tuple[str, Any]] = list(request.params.items())
    if isinstance(request.body, dict):
        items += list(request.body.items())
    elif request.body is not None:
        items.append(("body", request.body))
    fields: list[tuple[str, str]] = []
    remaining = TOTAL_PREVIEW_MAX
    truncated = False
    for name, value in items:
        text = scrub_text(_render(value))
        room = min(FIELD_PREVIEW_MAX, remaining)
        if len(text) > room:
            truncated = True
            text = text[:room] + ("…" if room else "")
            remaining -= room
        else:
            remaining -= len(text)
        fields.append((clip(name, 60), text))
    return fields, truncated


def summarize(tool: ToolSpec, request: ToolRequest) -> str:
    """Le résumé que January lit : ce que fait l'outil, la route visée et, pour chaque argument
    (6 au plus), son nom et un court aperçu entre guillemets. Les clés sont masquées, rien n'est
    interprété : un texte piégé reste un texte."""
    what = (tool.summary or tool.description).strip()
    parts: list[str] = []
    fields = dict(request.params)
    if isinstance(request.body, dict):
        fields.update(request.body)
    for name, value in list(fields.items())[:_PREVIEW_FIELDS]:
        if isinstance(value, str | int | float | bool):
            parts.append(f"{clip(name, 30)} = « {clip(scrub_text(str(value)), _PREVIEW)} »")
        else:
            parts.append(clip(name, 30))
    text = f"{what} — {request.method} {request.path}"
    if parts:
        text += " — " + " ; ".join(parts)
    return text[:1000]
