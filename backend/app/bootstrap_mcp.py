"""Composition du serveur MCP (phase 10) : le registre des actions assemblé depuis
`MCP_FEATURES`, la porte (jetons, limites, journal) et l'envoyeur. Vide pour l'instant : 10.B1 et
10.B2 le remplissent. Comme `app.bootstrap`, seul `app.main` l'importe, par `app.bootstrap`
(contrat 5)."""

from fastapi import FastAPI


def compose_mcp(app: FastAPI) -> None:
    """Pose sur `app.state` ce que la porte MCP lit. Rien avant 10.B1."""
