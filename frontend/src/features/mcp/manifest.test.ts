import { describe, expect, it } from "vitest";
import { mcpManifest } from "./manifest";

describe("mcpManifest", () => {
  it("manifest registers the settings entry", () => {
    expect(mcpManifest.id).toBe("mcp");
    expect(mcpManifest.routes.map((route) => route.path)).toEqual(["reglages/mcp"]);
    expect(mcpManifest.nav).toEqual([
      { section: "settings", labelKey: "mcp.nav.access", path: "/reglages/mcp", order: 9 },
    ]);
  });

  it("puts the pending badge in the top bar", () => {
    expect(mcpManifest.shell?.topbar).toBeDefined();
  });
});
