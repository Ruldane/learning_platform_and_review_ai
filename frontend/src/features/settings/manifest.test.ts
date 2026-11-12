import { describe, expect, it } from "vitest";
import { settingsManifest } from "./manifest";

describe("settingsManifest", () => {
  it("déclare la section Réglages, l'écran Modèles et clés et l'écran Recherche web", () => {
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
    ]);
    expect(settingsManifest.routes.map((route) => route.path)).toEqual([
      "reglages/modeles",
      "reglages/recherche",
    ]);
  });
});
