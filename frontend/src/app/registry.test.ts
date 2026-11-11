import { describe, expect, it } from "vitest";
import { buildNav } from "./buildNav";
import { FEATURES } from "./registry";

describe("registre des features", () => {
  it("a des identifiants uniques", () => {
    const ids = FEATURES.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("expose l'accueil et les réglages dans la navigation", () => {
    const groups = buildNav(FEATURES);
    expect(groups.map((g) => g.section)).toEqual(["home", "settings"]);
    expect(groups[0]?.items).toEqual([{ labelKey: "nav.home", path: "/" }]);
    expect(groups[1]?.items).toEqual([
      { labelKey: "settings.models.navLabel", path: "/reglages/modeles" },
    ]);
  });
});
