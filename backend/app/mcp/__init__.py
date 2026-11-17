"""Moteur du serveur MCP (phase 10, P10 à P19) : ce n'est pas une feature. Chaque feature déclare
ses actions dans `features/<f>/mcp.py` (`MCP: FeatureMcp`) ; le registre `MCP_FEATURES` les
assemble. Ce paquet n'importe aucune feature ni `app.agents` (contrat d'import 9) : il ne connaît
que les déclarations (`base`) et appelle la vraie route de l'application."""
