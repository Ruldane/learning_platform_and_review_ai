import { describe, expect, it } from "vitest";
import { quizManifest } from "./manifest";

describe("quizManifest", () => {
  it("declares the reviews, the quiz list and the quiz page", () => {
    expect(quizManifest.id).toBe("quiz");
    expect(quizManifest.routes.map((route) => route.path)).toEqual([
      "etudier/revisions",
      "etudier/quiz",
      "etudier/quiz/:quizId",
    ]);
    expect(quizManifest.nav).toEqual([
      { section: "study", labelKey: "quiz.nav.reviews", path: "/etudier/revisions", order: 2 },
      { section: "study", labelKey: "quiz.nav.quiz", path: "/etudier/quiz", order: 3 },
    ]);
  });
});
