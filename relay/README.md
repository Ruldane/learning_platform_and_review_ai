# Relais Tremplin

Quand le menu « Qui fait tourner les agents » vaut **Claude Code (MCP)** ou **Codex (MCP)**, un parcours lancé dans Tremplin attend son client. Le relais interroge Tremplin toutes les deux minutes et lance ce client en arrière-plan. Au repos, il consomme au plus 720 des 1 000 appels quotidiens de son jeton. Il lance au plus deux clients à la fois, un par session, et arrête un client au bout de 20 min.

## Installation (une fois)

1. Lancer `node relay/install.mjs`. Le relais démarre aussitôt, fenêtre cachée, puis à chaque ouverture de la session Windows.
2. Ouvrir **Réglages → Accès MCP** et allumer l’accès MCP. Dans **Relais local**, cliquer sur **Connecter le relais**.

Le navigateur remet un code à usage unique, valable deux minutes, au relais sur `127.0.0.1:8770`. Le relais l’échange auprès de son API configurée et conserve son jeton dédié dans `%APPDATA%\Tremplin\relay-pairing.json`. Le jeton expire après 30 jours. Renouveler l’appairage révoque le jeton précédent. Le même écran permet de vérifier les portées manquantes et de révoquer l’appairage.

Avant le premier appairage, le relais accepte aussi `TREMPLIN_MCP_TOKEN` ou le champ `token` de `%APPDATA%\Tremplin\relay.json`.

Pour le retirer : `node relay/uninstall.mjs`. Son journal est dans `%APPDATA%\Tremplin\relay.log` et ne contient que des identifiants.

## Variables

- `TREMPLIN_MCP_URL` : l'adresse du serveur MCP, `http://127.0.0.1:8000/mcp` par défaut.
- `TREMPLIN_RELAY_ORIGINS` : les origines exactes de l’interface autorisées à appairer ce relais, séparées par des virgules. Les valeurs par défaut sont `http://localhost:5173` et `http://127.0.0.1:5173`. Utiliser une origine `localhost` ou `127.0.0.1` pour un autre port local.
- `TREMPLIN_RELAY_CLAUDE_MODEL` : le modèle de Claude Code pour les étapes jouées, `sonnet` par défaut (lettres, chiffres, `.`, `_` et `-` seulement ; sinon `sonnet`).
- `TREMPLIN_RELAY_MCP_CONFIG` : une configuration MCP pour Claude Code, quand la pile visée n'est pas celle qui y est branchée (pile de recette).

Claude Code est lancé depuis la racine du dépôt, là où le serveur `tremplin` est branché. Il ne reçoit que les outils de jeu (`agents_play_brief`, `agents_play_submit`, `sessions_get_session`) et la recherche web. La consigne envoyée au client est dans `prompt.md`.
