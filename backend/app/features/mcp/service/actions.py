"""Les tables que l'interface montre : les features qui déclarent des outils MCP (outils par
niveau) et la liste des outils exposés avec leur niveau. Lues du registre assemblé au démarrage."""

from app.features.mcp.schemas import McpActionOut, McpFeatureOut
from app.mcp.registry import Registry
from app.mcp.tools import ToolSpec


def _route(tool: ToolSpec) -> str | None:
    return f"{tool.route[0]} {tool.route[1]}" if tool.route else None


def list_actions(registry: Registry) -> list[McpActionOut]:
    return [
        McpActionOut(
            name=tool.name,
            feature=tool.feature,
            kind="graph" if tool.graph else "route",
            route=_route(tool),
            level=tool.level,
            summary=tool.summary,
            side_effects=tool.side_effects,
            untrusted=list(tool.untrusted),
        )
        for tool in sorted(registry.all(), key=lambda t: (t.feature, t.name))
    ]


def list_features(registry: Registry) -> list[McpFeatureOut]:
    counts: dict[str, list[int]] = {}
    for tool in registry.all():
        counts.setdefault(tool.feature, [0, 0, 0])[tool.level - 1] += 1
    return [
        McpFeatureOut(feature=name, read_actions=c[0], write_actions=c[1], confirm_actions=c[2])
        for name, c in sorted(counts.items())
    ]
