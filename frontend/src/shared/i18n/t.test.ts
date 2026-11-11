import { describe, expect, it } from "vitest";
import { t } from "./t";

describe("t", () => {
  it("interpole les variables", () => {
    expect(t("settings.keys.last4", { last4: "1234" })).toBe("•••• 1234");
  });

  it("renvoie le texte tel quel sans variables", () => {
    expect(t("app.name")).toBe("Tremplin");
  });

  it("laisse un marqueur sans valeur intact", () => {
    expect(t("settings.keys.last4", {})).toBe("•••• {last4}");
  });

  it("accepte les nombres", () => {
    expect(t("settings.keys.last4", { last4: 42 })).toBe("•••• 42");
  });

  it("refuse une clé inconnue à la compilation", () => {
    // @ts-expect-error la clé n'existe pas dans `fr`
    expect(t("n.existe.pas")).toBe("n.existe.pas");
  });
});
