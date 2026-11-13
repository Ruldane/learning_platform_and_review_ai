import { describe, expect, it } from "vitest";
import { captureManifest } from "./manifest";

describe("captureManifest", () => {
  it("declares the journal, its entry in Étudier and the top bar and overlay slots", () => {
    expect(captureManifest.id).toBe("capture");
    expect(captureManifest.routes.map((route) => route.path)).toEqual(["etudier/journal"]);
    expect(captureManifest.nav).toEqual([
      { section: "study", labelKey: "capture.nav.journal", path: "/etudier/journal", order: 4 },
    ]);
    expect(captureManifest.shell?.topbar).toBeDefined();
    expect(captureManifest.shell?.overlay).toBeDefined();
  });
});
