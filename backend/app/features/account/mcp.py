"""Déclaration MCP de `account` : niveau 4, rien n'est exposé (export et suppression du compte)."""

from app.mcp.base import FeatureMcp

_WHY = (
    "Compte et ses données (export complet, suppression totale) : niveau 4, jamais exposé au "
    "MCP ; January le fait elle-même depuis l'interface."
)

MCP = FeatureMcp(
    feature="account",
    excluded={route: _WHY for route in ("GET /account/export", "POST /account/delete")},
)
