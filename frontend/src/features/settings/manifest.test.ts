import { describe, expect, it } from "vitest";
import { settingsManifest } from "./manifest";

describe("settingsManifest", () => {
  it("déclare la section Réglages, l'écran Modèles et clés, l'écran Recherche web et l'écran Étude et bilan", () => {
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
        labelKey: "settings.study.navLabel",
        path: "/reglages/etude",
        order: 4,
      },
    ]);
    expect(settingsManifest.routes.map((route) => route.path)).toEqual([
      "reglages/modeles",
      "reglages/recherche",
      "reglages/etude",
    ]);
  });
});
