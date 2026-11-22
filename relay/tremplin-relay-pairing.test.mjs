import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  createPairingHandler, readPairingToken, RELAY_PAIRING_PORT, storePairingToken,
} from "./tremplin-relay-pairing.mjs";

const origin = "http://localhost:5173";
const code = `trp_${"F".repeat(43)}`;
const token = `tmcp_${"T".repeat(43)}`;
const host = `127.0.0.1:${RELAY_PAIRING_PORT}`;
const headers = { host, origin, "content-type": "application/json" };

async function request(handler, options = {}) {
  const req = {
    url: options.url ?? "/pair", method: options.method ?? "POST",
    headers: options.headers ?? headers,
    async *[Symbol.asyncIterator]() {
      yield Buffer.from(options.body ?? JSON.stringify({ code }));
    },
  };
  const res = {
    headers: {}, body: "", statusCode: 200,
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(body) { this.body = body ?? ""; },
  };
  await handler(req, res);
  return res;
}

test("preflight requires the exact configured origin and loopback host", async () => {
  const handler = createPairingHandler({
    origins: [origin], getUrl: () => { throw Error("should not exchange"); },
  });
  const preflight = { ...headers, "access-control-request-method": "POST",
    "access-control-request-headers": "content-type", "access-control-request-private-network": "true" };
  const allowed = await request(handler, { headers: preflight, method: "OPTIONS" });
  assert.equal(allowed.statusCode, 204);
  assert.equal(allowed.headers["access-control-allow-origin"], origin);
  assert.equal(allowed.headers["access-control-allow-private-network"], "true");
  for (const deniedHeaders of [
    { ...preflight, origin: `${origin}.example.test` }, { ...preflight, origin: "http://localhost:5175" },
    { ...preflight, origin: undefined }, { ...preflight, host: `example.test:${RELAY_PAIRING_PORT}` },
  ]) {
    const denied = await request(handler, { headers: deniedHeaders, method: "OPTIONS" });
    assert.equal(denied.statusCode, 403);
    assert.equal(denied.headers["access-control-allow-origin"], undefined);
  }
});

test("exchange follows the configured API and replies without the token", async () => {
  const stored = [];
  const requests = [];
  const handler = createPairingHandler({
    origins: [origin], getUrl: () => "http://127.0.0.1:8008/mcp",
    storeToken: (value) => stored.push(value),
    fetcher: async (url, options) => {
      requests.push([String(url), options]);
      return Response.json({ token }, { status: 201 });
    },
  });
  const malicious = await request(handler, { body: JSON.stringify({ code, url: "http://outside.example" }) });
  assert.equal(malicious.statusCode, 400);
  assert.deepEqual(requests, []);
  const exchanged = await request(handler);
  assert.equal(exchanged.statusCode, 204);
  assert.equal(exchanged.body, "");
  assert.deepEqual(stored, [token]);
  assert.equal(requests[0][0], "http://127.0.0.1:8008/api/v1/mcp/relay/exchange");
  assert.equal(requests[0][1].redirect, "error");
  assert.deepEqual(JSON.parse(requests[0][1].body), { code });
});

test("refused exchanges preserve the previous token and never relay the API response", async () => {
  const handler = createPairingHandler({
    origins: [origin], getUrl: () => "http://localhost:8000/mcp",
    storeToken: () => { throw Error("should not store"); },
    fetcher: async () => Response.json({ secret: code }, { status: 401 }),
  });
  const refused = await request(handler);
  assert.equal(refused.statusCode, 409);
  assert.equal(refused.body.includes(code), false);
  assert.equal(refused.body.includes(token), false);
});

test("paired token is kept in its own file and survives a renewal", async () => {
  const directory = await mkdtemp(join(tmpdir(), "tremplin-pair-test-"));
  try {
    assert.equal(readPairingToken(directory), undefined);
    storePairingToken(directory, token);
    assert.equal(readPairingToken(directory), token);
    const renewed = `tmcp_${"R".repeat(43)}`;
    storePairingToken(directory, renewed);
    assert.equal(readPairingToken(directory), renewed);
    assert.equal((await readFile(join(directory, "relay-pairing.json"), "utf8")).includes(token), false);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
