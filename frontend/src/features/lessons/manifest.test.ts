import { describe, expect, it } from "vitest";
import { makeLessonsManifest } from "./manifest";

const lessonsManifest = makeLessonsManifest();

describe("lessonsManifest", () => {
  it("declares Leçons and Bibliothèque under Apprendre, after Programme", () => {
    expect(lessonsManifest.id).toBe("lessons");
    expect(lessonsManifest.nav?.map((entry) => [entry.path, entry.order])).toEqual([
      ["/learn/lessons", 4],
      ["/learn/library", 5],
    ]);
    expect(lessonsManifest.nav?.every((entry) => entry.section === "learn")).toBe(true);
  });

  it("declares the lessons, lesson and library routes", () => {
    expect(lessonsManifest.routes.map((route) => route.path)).toEqual([
      "learn/lessons",
      "learn/lessons/:lessonId",
      "learn/library",
    ]);
  });
});
