import { describe, expect, it } from "vitest";
import { costsManifest } from "./manifest";

describe("costsManifest", () => {
  it("adds Coûts and Journal des agents to the Réglages section, after the study settings", () => {
    expect(costsManifest.id).toBe("costs");
    expect(costsManifest.routes.map((route) => route.path)).toEqual([
      "reglages/couts",
      "reglages/journal",
    ]);
    expect(costsManifest.nav).toEqual([
      { section: "settings", labelKey: "costs.nav.costs", path: "/reglages/couts", order: 6 },
      { section: "settings", labelKey: "costs.nav.log", path: "/reglages/journal", order: 7 },
    ]);
  });
});
