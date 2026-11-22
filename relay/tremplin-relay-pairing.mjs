import { randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { join } from "node:path";

export const RELAY_PAIRING_PORT = 8770;
const LOOPBACK = "127.0.0.1";
const PAIRING_HOST = `${LOOPBACK}:${RELAY_PAIRING_PORT}`;
const EXCHANGE_PATH = "/api/v1/mcp/relay/exchange";
const SECRET = /^[A-Za-z0-9_-]{43}$/;
const MAX_BODY = 256;
const API_TIMEOUT = 8_000;
const LOCAL_HOSTS = new Set(["localhost", LOOPBACK]);

function isSecret(value, prefix) {
  return typeof value === "string" && value.startsWith(prefix) && SECRET.test(value.slice(prefix.length));
}

function isLoopback(url) {
  return LOCAL_HOSTS.has(url.hostname) && ["http:", "https:"].includes(url.protocol);
}

function exactLocalOrigin(origin) {
  try {
    const url = new URL(origin);
    return isLoopback(url) && origin === url.origin;
  } catch {
    return false;
  }
}

function pairingOrigins() {
  return (process.env.TREMPLIN_RELAY_ORIGINS ?? "http://localhost:5173,http://127.0.0.1:5173")
    .split(",").map((origin) => origin.trim()).filter(exactLocalOrigin);
}

export function readPairingToken(directory) {
  try {
    const { token } = JSON.parse(readFileSync(join(directory, "relay-pairing.json"), "utf8"));
    return isSecret(token, "tmcp_") ? token : undefined;
  } catch {
    return undefined;
  }
}

export function storePairingToken(directory, token) {
  if (!isSecret(token, "tmcp_")) throw new Error("pairing_invalid_token");
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const draft = join(directory, `relay-pairing-${randomUUID()}.tmp`);
  try {
    writeFileSync(draft, JSON.stringify({ token }), { flag: "wx", mode: 0o600 });
    renameSync(draft, join(directory, "relay-pairing.json"));
  } finally {
    rmSync(draft, { force: true });
  }
}

function respond(response, status) {
  response.statusCode = status;
  response.setHeader("Cache-Control", "no-store");
  response.end();
}

function acceptPreflight(request, response) {
  const method = request.headers["access-control-request-method"];
  const headers = request.headers["access-control-request-headers"] ?? "";
  if (method !== "POST" || headers.toLowerCase() !== "content-type") return respond(response, 403);
  response.setHeader("Access-Control-Allow-Methods", "POST");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (request.headers["access-control-request-private-network"] === "true") {
    response.setHeader("Access-Control-Allow-Private-Network", "true");
  }
  return respond(response, 204);
}

async function readCode(request) {
  let body = "";
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY) return null;
    body += chunk.toString("ascii");
  }
  const data = JSON.parse(body);
  if (!data || !isSecret(data.code, "trp_") || Object.keys(data).length !== 1) return null;
  return data.code;
}

async function exchange(code, mcpUrl, fetcher, storeToken) {
  const api = new URL(mcpUrl);
  if (!isLoopback(api) || api.username || api.password) return 502;
  const result = await fetcher(new URL(EXCHANGE_PATH, api), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
    redirect: "error",
    signal: AbortSignal.timeout(API_TIMEOUT),
  });
  if (result.status === 401 || result.status === 403) return 409;
  if (result.status !== 201) return 502;
  const { token } = await result.json();
  if (!isSecret(token, "tmcp_")) return 502;
  await storeToken(token);
  return 204;
}

export function createPairingHandler({ getUrl, storeToken, origins = pairingOrigins(), fetcher = fetch }) {
  const allowed = new Set(origins.filter(exactLocalOrigin));
  let exchanging = false;
  return async (request, response) => {
    const { origin, host } = request.headers;
    if (host !== PAIRING_HOST || !allowed.has(origin)) return respond(response, 403);
    response.setHeader("Access-Control-Allow-Origin", origin);
    response.setHeader("Vary", "Origin");
    if (request.url !== "/pair") return respond(response, 404);
    if (request.method === "OPTIONS") return acceptPreflight(request, response);
    if (request.method !== "POST") return respond(response, 405);
    if (request.headers["content-type"] !== "application/json") return respond(response, 415);
    const code = await readCode(request).catch(() => null);
    if (!code) return respond(response, 400);
    if (exchanging) return respond(response, 409);
    exchanging = true;
    try {
      return respond(response, await exchange(code, getUrl(), fetcher, storeToken));
    } catch {
      return respond(response, 502);
    } finally {
      exchanging = false;
    }
  };
}

export function startPairingServer(directory, getUrl, onFailure) {
  const handle = createPairingHandler({
    getUrl,
    storeToken: (token) => storePairingToken(directory, token),
  });
  const server = createServer({ requestTimeout: 10_000, headersTimeout: 5_000 }, (request, response) => {
    void handle(request, response);
  });
  server.on("error", onFailure);
  server.listen(RELAY_PAIRING_PORT, LOOPBACK);
  return server;
}
