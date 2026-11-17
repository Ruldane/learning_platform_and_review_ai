import { describe, expect, it } from "vitest";
import { accountManifest } from "./manifest";

describe("accountManifest", () => {
  it("adds Mes données to the Réglages section, after the costs and the log", () => {
    expect(accountManifest.id).toBe("account");
    expect(accountManifest.routes.map((route) => route.path)).toEqual(["reglages/donnees"]);
    expect(accountManifest.nav).toEqual([
      { section: "settings", labelKey: "account.nav.data", path: "/reglages/donnees", order: 8 },
    ]);
  });
});
