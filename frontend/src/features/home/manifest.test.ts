import { describe, expect, it } from "vitest";
import { homeManifest } from "./manifest";

describe("homeManifest", () => {
  it("declares the wide index route, its entry and the notifications overlay", () => {
    expect(homeManifest.id).toBe("home");
    expect(homeManifest.routes).toHaveLength(1);
    expect(homeManifest.routes[0]?.index).toBe(true);
    expect(homeManifest.routes[0]?.handle).toEqual({ wide: true });
    expect(homeManifest.nav).toEqual([
      { section: "home", labelKey: "nav.home", path: "/", order: 1 },
    ]);
    expect(homeManifest.shell?.overlay).toBeDefined();
    expect(homeManifest.shell?.topbar).toBeUndefined();
  });
});
