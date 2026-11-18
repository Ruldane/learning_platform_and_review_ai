// Relais de Tremplin : quand un parcours lancé avec « Claude Code (MCP) » ou « Codex (MCP) »
// attend son client, lance ce client en arrière-plan pour le jouer, sans geste de January.
// Jeton : TREMPLIN_MCP_TOKEN (le même que Codex), sinon %APPDATA%\Tremplin\relay.json {"token"}.
// Adresse : TREMPLIN_MCP_URL, sinon http://127.0.0.1:8000/mcp. Journal : identifiants seulement.
import { spawn } from "node:child_process";
import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = dirname(here); // Claude Code y trouve le serveur `tremplin` branché sur ce dossier
const appDir = join(process.env.APPDATA ?? join(homedir(), ".config"), "Tremplin");
const POLL_MS = 10_000;
const MAX_RUNNING = 2;
const RUN_TIMEOUT_MS = 20 * 60_000;
const running = new Map(); // session_id -> processus du client

function log(line) {
  mkdirSync(appDir, { recursive: true });
  appendFileSync(join(appDir, "relay.log"), `${new Date().toISOString()} ${line}\n`);
}

function config() {
  let saved = {};
  try {
    saved = JSON.parse(readFileSync(join(appDir, "relay.json"), "utf8"));
  } catch {
    // pas de fichier : variables d'environnement seulement
  }
  const url = process.env.TREMPLIN_MCP_URL ?? saved.url ?? "http://127.0.0.1:8000/mcp";
  return { url, token: process.env.TREMPLIN_MCP_TOKEN ?? saved.token };
}

async function call(cfg, name, args) {
  const origin = new URL(cfg.url).origin;
  const r = await fetch(cfg.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${cfg.token}`,
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      Origin: origin,
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: { name, arguments: args },
    }),
  });
  if (r.status === 429) return { wait: Number(r.headers.get("retry-after") ?? 60) * 1000 };
  const text = await r.text();
  const line = text.split("\n").find((l) => l.startsWith("data:"));
  const body = JSON.parse(line ? line.slice(5) : text);
  const result = body.result ?? {};
  const raw = result.structuredContent ?? JSON.parse(result.content?.[0]?.text ?? "{}");
  return { data: raw.data ?? raw };
}

const PROMPT = readFileSync(join(here, "prompt.md"), "utf8");

// Une autre pile que celle branchée dans Claude Code (pile de recette) : sa configuration MCP.
function claudeServer() {
  const path = process.env.TREMPLIN_RELAY_MCP_CONFIG;
  return path ? ["--mcp-config", `"${path}"`, "--strict-mcp-config"] : [];
}

function launch(client, sessionId) {
  const prompt = PROMPT.replaceAll("{session_id}", sessionId);
  const tools = [
    "mcp__tremplin__agents_play_brief",
    "mcp__tremplin__agents_play_submit",
    "mcp__tremplin__sessions_get_session",
    "WebSearch",
    "WebFetch",
  ].join(",");
  const [cmd, args] =
    client === "codex"
      ? ["codex", ["exec", "--skip-git-repo-check", "--ephemeral", "--search", "-c", "approval_policy=never", "-"]]
      : ["claude", ["-p", "--allowedTools", tools, "--output-format", "text", ...claudeServer()]];
  // Arguments fixes seulement ; la consigne passe par l'entrée standard (aucune mise entre
  // guillemets par le shell de Windows).
  const child = spawn(cmd, args, { cwd: repo, shell: true, windowsHide: true, stdio: ["pipe", "ignore", "ignore"] });
  child.stdin.end(prompt);
  const timer = setTimeout(() => child.kill(), RUN_TIMEOUT_MS);
  running.set(sessionId, child);
  log(`lancé ${client} pour la session ${sessionId}`);
  child.on("exit", (code) => {
    clearTimeout(timer);
    running.delete(sessionId);
    log(`fin ${client} session ${sessionId} code ${code}`);
  });
  child.on("error", (err) => {
    clearTimeout(timer);
    running.delete(sessionId);
    log(`client ${client} introuvable (${err.code ?? "erreur"})`);
  });
}

async function tick(cfg) {
  const out = await call(cfg, "sessions_list_sessions", { status: "waiting_user" });
  if (out.wait) return out.wait;
  const rows = Array.isArray(out.data) ? out.data : (out.data?.items ?? []);
  for (const row of rows) {
    if (running.size >= MAX_RUNNING) break;
    const client = row.played_by;
    if (client !== "claude-code" && client !== "codex") continue;
    if (row.pending_interrupt?.kind !== "mcp_model" || running.has(row.id)) continue;
    launch(client, row.id);
  }
  return POLL_MS;
}

async function main() {
  log("relais démarré");
  for (;;) {
    const cfg = config();
    let delay = POLL_MS;
    if (!cfg.token) {
      log("aucun jeton (TREMPLIN_MCP_TOKEN ou relay.json) : nouvel essai dans une minute");
      delay = 60_000;
    } else {
      try {
        delay = await tick(cfg);
      } catch (err) {
        delay = 30_000; // Tremplin arrêté ou injoignable : on réessaie calmement
        log(`Tremplin injoignable (${err.cause?.code ?? err.name})`);
      }
    }
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
}

await main();
