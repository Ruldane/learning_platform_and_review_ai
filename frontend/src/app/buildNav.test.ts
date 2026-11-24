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

  it("donne à chaque groupe la couleur de sa section", () => {
    const groups = buildNav([
      {
        id: "x",
        routes: [],
        nav: [
          { section: "learn", labelKey: "nav.learn", path: "/a", order: 1 },
          { section: "settings", labelKey: "nav.settings", path: "/r", order: 1 },
        ],
      },
    ]);
    expect(groups.map((group) => group.color)).toEqual([
      "var(--section-learn)",
      "var(--section-settings)",
    ]);
  });

  it("ne crée pas de groupe pour une feature sans entrée de navigation", () => {
    expect(buildNav([{ id: "health", routes: [] }])).toEqual([]);
  });

  it("buildNav ignores publicRoutes", () => {
    expect(
      buildNav([
        { id: "auth", routes: [], publicRoutes: [{ path: "/login", element: null }] },
        {
          id: "home",
          routes: [],
          nav: [{ section: "home", labelKey: "nav.home", path: "/", order: 1 }],
        },
      ]).flatMap((group) => group.items.map((item) => item.path)),
    ).toEqual(["/"]);
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

  it("transmet la pastille d'une entrée (hook et texte) et rien aux autres", () => {
    const useBadge = () => 2;
    const badgeLabel = (count: number) => `${count} relances dues`;
    const [group] = buildNav([
      {
        id: "applications",
        routes: [],
        nav: [
          { section: "applications", labelKey: "applications.nav.board", path: "/c", order: 1 },
          {
            section: "applications",
            labelKey: "applications.nav.reminders",
            path: "/c/relances",
            order: 2,
            useBadge,
            badgeLabel,
          },
        ],
      },
    ]);
    expect(group?.items[0]).toEqual({ labelKey: "applications.nav.board", path: "/c" });
    expect(group?.items[1]).toMatchObject({ useBadge, badgeLabel });
  });
});
