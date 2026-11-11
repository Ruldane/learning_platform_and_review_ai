import { describe, expect, it } from "vitest";
import { settingsManifest } from "./manifest";

describe("settingsManifest", () => {
  it("déclare la section Réglages et l'écran Modèles et clés", () => {
    expect(settingsManifest.id).toBe("settings");
    expect(settingsManifest.nav).toEqual({
      section: "settings",
      labelKey: "settings.models.navLabel",
      path: "/reglages/modeles",
      order: 1,
    });
    expect(settingsManifest.routes.map((route) => route.path)).toEqual(["reglages/modeles"]);
  });
});
