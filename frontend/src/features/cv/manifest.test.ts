import { describe, expect, it } from "vitest";
import { cvManifest } from "./manifest";

describe("cvManifest", () => {
  it("declares the profile, templates, review and versions routes", () => {
    expect(cvManifest.id).toBe("cv");
    expect(cvManifest.routes.map((route) => route.path)).toEqual([
      "career/profile",
      "career/cv",
      "career/cv/templates/:templateId",
      "career/cv/reviews/new/:postingId",
      "career/cv/reviews/:reviewId",
      "career/cv/versions",
    ]);
  });

  it("puts Profil first and CV second in the career section (G29)", () => {
    expect(cvManifest.nav).toEqual([
      { section: "career", labelKey: "cv.nav.profile", path: "/career/profile", order: 1 },
      { section: "career", labelKey: "cv.nav.cv", path: "/career/cv", order: 2 },
    ]);
  });

  it("serves the route the offer page links to for « Revoir mon CV »", () => {
    // `features/gap` lie vers `/career/cv/reviews/new/:postingId`.
    expect(cvManifest.routes.some((r) => r.path === "career/cv/reviews/new/:postingId")).toBe(
      true,
    );
  });
});
