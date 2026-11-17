import { describe, expect, it } from "vitest";
import { authManifest } from "./manifest";

describe("authManifest", () => {
  it("declares the gate and the account slot of the shell", () => {
    expect(authManifest.id).toBe("auth");
    expect(authManifest.shell?.gate).toBeDefined();
    expect(authManifest.shell?.topbar).toBeDefined();
  });

  it("has public routes only: no page inside the layout, no navigation entry", () => {
    expect(authManifest.routes).toEqual([]);
    expect(authManifest.nav).toBeUndefined();
    expect(authManifest.publicRoutes?.map((route) => route.path)).toEqual([
      "/connexion",
      "/connexion/reprise",
    ]);
  });
});
