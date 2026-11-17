import { describe, expect, it } from "vitest";
import manifestSource from "./manifest.ts?raw";
import { ideManifest } from "./manifest";

describe("ideManifest", () => {
  it("manifest has the code entry once", () => {
    expect(ideManifest.id).toBe("ide");
    expect(ideManifest.routes.map((route) => route.path)).toEqual(["code", "code/:sessionId"]);
    expect(ideManifest.nav).toEqual([
      { section: "study", labelKey: "ide.nav.code", path: "/code", order: 5 },
    ]);
  });

  it("gives the session the full width of the shell", () => {
    expect(ideManifest.routes[1]?.handle).toEqual({ wide: true });
  });

  it("loads the session page, and so Monaco, only when its route opens", async () => {
    const route = ideManifest.routes[1]!;
    expect(route.Component).toBeUndefined();
    expect(manifestSource).not.toMatch(/^import .*pages\/IdeSessionPage/m);
    const loaded = await (route.lazy as () => Promise<{ Component: unknown }>)();
    expect(typeof loaded.Component).toBe("function");
  }, 30_000);
});
