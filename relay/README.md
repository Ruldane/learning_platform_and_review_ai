# Relais Tremplin

Quand le menu « Qui fait tourner les agents » vaut **Claude Code (MCP)** ou **Codex (MCP)**, un parcours lancé dans Tremplin attend son client. Le relais interroge Tremplin toutes les deux minutes et lance ce client en arrière-plan. Au repos, il consomme au plus 720 des 1 000 appels quotidiens de son jeton. Il lance au plus deux clients à la fois, un par session, et arrête un client au bout de 20 min.

## Installation (une fois)

1. Créer un jeton MCP dédié au relais dans Réglages > Accès MCP. Le relais le lit dans `TREMPLIN_MCP_TOKEN` ou dans le champ `token` de `%APPDATA%\Tremplin\relay.json`.
2. `node relay/install.mjs` : le relais démarre avec Windows, fenêtre cachée, et tourne tout de suite.

Pour le retirer : `node relay/uninstall.mjs`. Son journal est dans `%APPDATA%\Tremplin\relay.log` et ne contient que des identifiants.

## Variables

- `TREMPLIN_MCP_URL` : l'adresse du serveur MCP, `http://127.0.0.1:8000/mcp` par défaut.
- `TREMPLIN_RELAY_MCP_CONFIG` : une configuration MCP pour Claude Code, quand la pile visée n'est pas celle qui y est branchée (pile de recette).

Claude Code est lancé depuis la racine du dépôt, là où le serveur `tremplin` est branché. Il ne reçoit que les outils de jeu (`agents_play_brief`, `agents_play_submit`, `sessions_get_session`) et la recherche web. La consigne envoyée au client est dans `prompt.md`.
