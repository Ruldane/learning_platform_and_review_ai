import { describe, expect, it } from "vitest";
import { confirmationOut } from "@/test/mcpApi";
import { toCallView, toConfirmationView, toVerdict } from "./toView";
import type { McpCallOut, McpConfirmationOut } from "./types";

const NOW = new Date("2026-11-17T12:00:00Z");
const confirmation = (over: Record<string, unknown> = {}) =>
  confirmationOut(over) as McpConfirmationOut;

describe("toConfirmationView", () => {
  it("turns a pending request whose deadline has passed into an expired one", () => {
    const view = toConfirmationView(
      confirmation({ expires_at: "2026-11-17T11:59:00Z" }),
      new Map(),
      NOW,
    );
    expect(view.state).toBe("expired");
  });

  it("keeps a request waiting before its deadline, and names the token", () => {
    const view = toConfirmationView(confirmation(), new Map([["tk1", "Portable"]]), NOW);
    expect(view.state).toBe("pending");
    expect(view.tokenLabel).toBe("Portable");
  });
});

describe("toVerdict", () => {
  it("is null without precheck", () => expect(toVerdict(null)).toBeNull());

  it("only trusts an explicit ok: true", () => {
    expect(toVerdict({ reasons: [] })?.ok).toBe(false);
    expect(toVerdict({ ok: "yes" })?.ok).toBe(false);
    expect(toVerdict({ ok: true, reasons: ["a", 3], summary: 4 })).toEqual({
      ok: true,
      reasons: ["a"],
      summary: null,
    });
  });
});

describe("toCallView", () => {
  const call = (over: Record<string, unknown> = {}) =>
    ({
      id: "c1",
      token_id: "tk1",
      action: "cv_list",
      level: 1,
      code: 200,
      duration_ms: 12,
      ids: {},
      created_at: "2026-11-17T09:00:00Z",
      ...over,
    }) as McpCallOut;

  it("names the token, or leaves it unknown", () => {
    expect(toCallView(call(), new Map([["tk1", "Portable"]])).tokenLabel).toBe("Portable");
    expect(toCallView(call({ token_id: "gone" }), new Map()).tokenLabel).toBeNull();
    expect(toCallView(call({ token_id: null }), new Map()).tokenLabel).toBeNull();
  });
});
