import assert from "node:assert/strict";
import { test } from "node:test";
import { clientCommand, tick } from "./tremplin-relay.mjs";

test("idle relay leaves at least 250 MCP calls available per day", async () => {
  const calls = [];
  const pollMs = await tick({}, async (_config, tool, args) => {
    calls.push({ tool, args });
    return { data: [] };
  });

  assert.deepEqual(calls, [
    { tool: "sessions_list_sessions", args: { status: "waiting_user" } },
  ]);
  assert.equal(pollMs, 120_000);
  assert.ok(Math.ceil(24 * 60 * 60_000 / pollMs) <= 750);
});

test("relay respects a longer MCP rate-limit delay", async () => {
  const retryAfterMs = 43 * 60_000;
  assert.equal(await tick({}, async () => ({ wait: retryAfterMs })), retryAfterMs);
});

test("Codex receives search as a global option", () => {
  const [command, args] = clientCommand("codex");
  assert.equal(command, "codex");
  assert.deepEqual(args.slice(0, 2), ["--search", "exec"]);
  assert.ok(args.includes("--ephemeral"));
  assert.equal(args.at(-1), "-");
});

test("Claude Code plays on Sonnet by default", () => {
  const [command, args] = clientCommand("claude-code", {});
  assert.equal(command, "claude");
  const at = args.indexOf("--model");
  assert.ok(at >= 0);
  assert.equal(args[at + 1], "sonnet");
});

test("TREMPLIN_RELAY_CLAUDE_MODEL picks another model", () => {
  const [, args] = clientCommand("claude-code", { TREMPLIN_RELAY_CLAUDE_MODEL: "haiku" });
  assert.equal(args[args.indexOf("--model") + 1], "haiku");
});

test("an unsafe model name falls back to Sonnet", () => {
  const [, args] = clientCommand("claude-code", { TREMPLIN_RELAY_CLAUDE_MODEL: "x & del" });
  assert.equal(args[args.indexOf("--model") + 1], "sonnet");
});
