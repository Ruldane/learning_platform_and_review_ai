import { describe, expect, it } from "vitest";
import { learningManifest } from "./manifest";

describe("learningManifest", () => {
  it("declares Objectifs and Conseil under Apprendre", () => {
    expect(learningManifest.id).toBe("learning");
    expect(learningManifest.nav?.map((n) => n.path)).toEqual([
      "/learn/goals",
      "/learn/council",
    ]);
    expect(learningManifest.nav?.every((n) => n.section === "learn")).toBe(true);
    expect(learningManifest.nav?.map((n) => n.order)).toEqual([1, 2]);
  });

  it("declares the three routes", () => {
    expect(learningManifest.routes.map((route) => route.path)).toEqual([
      "learn/goals",
      "learn/goals/:goalId/council",
      "learn/council",
    ]);
  });
});
