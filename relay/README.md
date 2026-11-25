# Tremplin relay

When **Who runs the agents** is set to **Claude Code (MCP)** or **Codex (MCP)**, a workflow launched in Tremplin waits for its client. The relay checks Tremplin every two minutes and starts that client in the background. When idle, it uses at most 720 of its token's 1,000 daily calls. It runs at most two clients at a time, one per session, and stops a client after 20 minutes.

## Installation (once)

1. Run `node relay/install.mjs`. The relay starts right away in a hidden window, then at every Windows sign-in.
2. Open **Settings → MCP access** and turn MCP access on. Under **Local relay**, click **Connect the relay**.

The browser hands a single-use code, valid for two minutes, to the relay on `127.0.0.1:8770`. The relay exchanges it with its configured API and keeps its dedicated token in `%APPDATA%\Tremplin\relay-pairing.json`. The token expires after 30 days. Renewing the pairing revokes the previous token. The same screen lets you check missing scopes and revoke the pairing.

Before the first pairing, the relay also accepts `TREMPLIN_MCP_TOKEN` or the `token` field of `%APPDATA%\Tremplin\relay.json`.

To remove it: `node relay/uninstall.mjs`. Its log is in `%APPDATA%\Tremplin\relay.log` and contains only identifiers.

## Variables

- `TREMPLIN_MCP_URL`: the MCP server address, `http://127.0.0.1:8000/mcp` by default.
- `TREMPLIN_RELAY_ORIGINS`: the exact interface origins allowed to pair this relay, separated by commas. The defaults are `http://localhost:5173` and `http://127.0.0.1:5173`. Use a `localhost` or `127.0.0.1` origin for another local port.
- `TREMPLIN_RELAY_CLAUDE_MODEL`: the Claude Code model for played steps, `sonnet` by default (letters, digits, `.`, `_` and `-` only; otherwise `sonnet`).
- `TREMPLIN_RELAY_MCP_CONFIG`: an MCP configuration for Claude Code, when the target stack is not the one connected there (a test stack).

Claude Code starts from the repository root, where the `tremplin` server is connected. It receives only the play tools (`agents_play_brief`, `agents_play_submit`, `sessions_get_session`) and web search. The instructions sent to the client are in `prompt.md`.
