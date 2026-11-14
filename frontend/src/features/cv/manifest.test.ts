import { describe, expect, it } from "vitest";
import { cvManifest } from "./manifest";

describe("cvManifest", () => {
  it("declares the profile, templates, review and versions routes", () => {
    expect(cvManifest.id).toBe("cv");
    expect(cvManifest.routes.map((route) => route.path)).toEqual([
      "carriere/profil",
      "carriere/cv",
      "carriere/cv/modeles/:templateId",
      "carriere/cv/revue/nouvelle/:postingId",
      "carriere/cv/revues/:reviewId",
      "carriere/cv/versions",
    ]);
  });

  it("puts Profil first and CV second in the career section (G29)", () => {
    expect(cvManifest.nav).toEqual([
      { section: "career", labelKey: "cv.nav.profile", path: "/carriere/profil", order: 1 },
      { section: "career", labelKey: "cv.nav.cv", path: "/carriere/cv", order: 2 },
    ]);
  });

  it("serves the route the offer page links to for « Revoir mon CV »", () => {
    // `features/gap` lie vers `/carriere/cv/revue/nouvelle/:postingId`.
    expect(cvManifest.routes.some((r) => r.path === "carriere/cv/revue/nouvelle/:postingId")).toBe(
      true,
    );
  });
});
