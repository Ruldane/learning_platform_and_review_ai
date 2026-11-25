import { describe, expect, it } from "vitest";
import { en } from "./en";
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
    // @ts-expect-error la clé n'existe pas dans `en`
    expect(t("n.existe.pas")).toBe("n.existe.pas");
  });

  it("merges sessions into session", () => {
    expect("sessions" in en).toBe(false);
    expect(t("session.errors.stale_interrupt")).toBe("This question has already been answered.");
    expect(t("session.stream.not_found")).toBe("This session can’t be found.");
    expect(t("session.status.paused")).toBe("Paused");
  });

  it("aggregates the memory zone", () => {
    expect(t("memory.kind.lesson")).toBe("Lesson");
    expect(t("memory.level.proven")).toBe("Proven");
    expect(t("memory.action.merge")).toBe("Merge");
    expect(t("memory.empty")).toBe("No items in memory");
    expect(t("memory.drawer.deleteAsk")).toBe("Delete permanently?");
  });
});
