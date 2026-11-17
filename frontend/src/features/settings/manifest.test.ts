import { describe, expect, it } from "vitest";
import { settingsManifest } from "./manifest";
import { OnboardingGate } from "./OnboardingGate";

describe("settingsManifest", () => {
  it("le premier lancement est une page nue : sans navigation latérale (handle bare)", () => {
    const welcome = settingsManifest.routes.find((route) => route.path === "bienvenue");
    expect(welcome?.handle).toEqual({ bare: true });
  });

  it("déclare la section Réglages et ses cinq écrans, dans l'ordre de la navigation", () => {
    expect(settingsManifest.id).toBe("settings");
    expect(settingsManifest.nav).toEqual([
      {
        section: "settings",
        labelKey: "settings.models.navLabel",
        path: "/reglages/modeles",
        order: 1,
      },
      {
        section: "settings",
        labelKey: "settings.search.navLabel",
        path: "/reglages/recherche",
        order: 2,
      },
      {
        section: "settings",
        labelKey: "settings.availability.navLabel",
        path: "/reglages/disponibilite",
        order: 3,
      },
      {
        section: "settings",
        labelKey: "settings.study.navLabel",
        path: "/reglages/etude",
        order: 4,
      },
      {
        section: "settings",
        labelKey: "settings.style.navLabel",
        path: "/reglages/style",
        order: 5,
      },
    ]);
    expect(settingsManifest.routes.map((route) => route.path)).toEqual([
      "reglages/modeles",
      "reglages/recherche",
      "reglages/disponibilite",
      "reglages/etude",
      "reglages/style",
      "bienvenue",
    ]);
  });

  it("puts the first launch behind a gate, and out of the navigation", () => {
    expect(settingsManifest.shell?.gate).toBe(OnboardingGate);
    // /bienvenue est une route, jamais une entrée de navigation.
    expect(settingsManifest.nav?.map((entry) => entry.path)).not.toContain("/bienvenue");
    expect(settingsManifest.publicRoutes).toBeUndefined();
  });
});
