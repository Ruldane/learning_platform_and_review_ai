import { describe, expect, it } from "vitest";
import { learningManifest } from "./manifest";

describe("learningManifest", () => {
  it("declares Objectifs and Conseil under Apprendre", () => {
    expect(learningManifest.id).toBe("learning");
    expect(learningManifest.nav?.map((n) => n.path)).toEqual([
      "/apprendre/objectifs",
      "/apprendre/conseil",
    ]);
    expect(learningManifest.nav?.every((n) => n.section === "learn")).toBe(true);
    expect(learningManifest.nav?.map((n) => n.order)).toEqual([1, 2]);
  });

  it("declares the three routes", () => {
    expect(learningManifest.routes.map((route) => route.path)).toEqual([
      "apprendre/objectifs",
      "apprendre/objectifs/:goalId/conseil",
      "apprendre/conseil",
    ]);
  });
});
