import { describe, expect, it } from "vitest";
import { gapManifest } from "./manifest";

describe("gapManifest", () => {
  it("declares the postings, posting and gap routes", () => {
    expect(gapManifest.id).toBe("gap");
    expect(gapManifest.routes.map((route) => route.path)).toEqual([
      "career/postings",
      "career/postings/:postingId",
      "career/gaps",
    ]);
  });

  it("puts Postings and Gaps in the career section after the profile and CV (G29)", () => {
    expect(gapManifest.nav).toEqual([
      { section: "career", labelKey: "gap.nav.postings", path: "/career/postings", order: 3 },
      { section: "career", labelKey: "gap.nav.overview", path: "/career/gaps", order: 4 },
    ]);
  });
});
