import { describe, expect, it } from "vitest";
import { lessonsManifest } from "./manifest";

describe("lessonsManifest", () => {
  it("declares Leçons and Bibliothèque under Apprendre, after Programme", () => {
    expect(lessonsManifest.id).toBe("lessons");
    expect(lessonsManifest.nav?.map((entry) => [entry.path, entry.order])).toEqual([
      ["/apprendre/lecons", 4],
      ["/apprendre/bibliotheque", 5],
    ]);
    expect(lessonsManifest.nav?.every((entry) => entry.section === "learn")).toBe(true);
  });

  it("declares the lessons, lesson and library routes", () => {
    expect(lessonsManifest.routes.map((route) => route.path)).toEqual([
      "apprendre/lecons",
      "apprendre/lecons/:lessonId",
      "apprendre/bibliotheque",
    ]);
  });
});
