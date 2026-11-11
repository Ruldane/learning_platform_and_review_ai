import { describe, expect, it } from "vitest";
import type { FeatureManifest } from "@/shared/lib/feature";
import { buildNav } from "./buildNav";

describe("buildNav", () => {
  it("garde l'ordre des sections et ignore les sections vides", () => {
    const groups = buildNav([
      {
        id: "settings",
        routes: [],
        nav: [{ section: "settings", labelKey: "nav.settings", path: "/reglages", order: 1 }],
      },
      {
        id: "home",
        routes: [],
        nav: [{ section: "home", labelKey: "nav.home", path: "/", order: 1 }],
      },
    ]);
    expect(groups.map((g) => g.section)).toEqual(["home", "settings"]);
  });

  it("ne crée pas de groupe pour une feature sans entrée de navigation", () => {
    expect(buildNav([{ id: "health", routes: [] }])).toEqual([]);
  });

  it("trie les entrées d'une section selon order", () => {
    const features: FeatureManifest[] = [
      {
        id: "b",
        routes: [],
        nav: [{ section: "learn", labelKey: "nav.study", path: "/b", order: 2 }],
      },
      {
        id: "a",
        routes: [],
        nav: [{ section: "learn", labelKey: "nav.learn", path: "/a", order: 1 }],
      },
    ];
    const [group] = buildNav(features);
    expect(group?.items.map((i) => i.path)).toEqual(["/a", "/b"]);
    expect(group?.labelKey).toBe("nav.learn");
  });

  it("accepte plusieurs entrées d'une même feature, triées par order avec les autres", () => {
    // SPEC 15.1 : la section Réglages compte plusieurs écrans d'une seule feature.
    const features: FeatureManifest[] = [
      {
        id: "settings",
        routes: [],
        nav: [
          { section: "settings", labelKey: "nav.study", path: "/reglages/style", order: 3 },
          { section: "settings", labelKey: "nav.learn", path: "/reglages/modeles", order: 1 },
        ],
      },
      {
        id: "other",
        routes: [],
        nav: [{ section: "settings", labelKey: "nav.home", path: "/reglages/dispo", order: 2 }],
      },
    ];
    const [group] = buildNav(features);
    expect(group?.items.map((i) => i.path)).toEqual([
      "/reglages/modeles",
      "/reglages/dispo",
      "/reglages/style",
    ]);
  });

  it("gère les 8 sections dans l'ordre de la spec", () => {
    const sections = [
      "settings",
      "memory",
      "applications",
      "career",
      "skills",
      "study",
      "learn",
      "home",
    ] as const;
    const features: FeatureManifest[] = sections.map((section) => ({
      id: section,
      routes: [],
      nav: [{ section, labelKey: "nav.home", path: `/${section}`, order: 1 }],
    }));
    expect(buildNav(features).map((g) => g.section)).toEqual([
      "home",
      "learn",
      "study",
      "skills",
      "career",
      "applications",
      "memory",
      "settings",
    ]);
  });
});
