import { describe, expect, it } from "vitest";
import { researchManifest } from "./manifest";

describe("researchManifest", () => {
  it("declares the research bench under Réglages", () => {
    expect(researchManifest.id).toBe("research");
    expect(researchManifest.nav?.[0]).toEqual({
      section: "settings",
      labelKey: "research.nav.bench",
      path: "/reglages/recherche/essai",
      order: 3,
    });
    expect(researchManifest.routes.map((route) => route.path)).toEqual([
      "reglages/recherche/essai",
    ]);
  });
});
