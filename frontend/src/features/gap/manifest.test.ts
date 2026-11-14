import { describe, expect, it } from "vitest";
import { gapManifest } from "./manifest";

describe("gapManifest", () => {
  it("declares the postings, posting and gap routes", () => {
    expect(gapManifest.id).toBe("gap");
    expect(gapManifest.routes.map((route) => route.path)).toEqual([
      "carriere/offres",
      "carriere/offres/:postingId",
      "carriere/ecarts",
    ]);
  });

  it("puts Offres and Écarts in the career section, after the profile and the CV (G29)", () => {
    expect(gapManifest.nav).toEqual([
      { section: "career", labelKey: "gap.nav.postings", path: "/carriere/offres", order: 3 },
      { section: "career", labelKey: "gap.nav.overview", path: "/carriere/ecarts", order: 4 },
    ]);
  });
});
