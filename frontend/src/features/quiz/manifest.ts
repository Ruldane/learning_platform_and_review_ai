import { createElement, type ComponentType } from "react";
import { MobilePage } from "./pages/MobilePage";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import type { FeatureManifest } from "@/shared/lib/feature";
import { QuizIndexPage } from "./pages/QuizIndexPage";
import { QuizPage } from "./pages/QuizPage";
import { ReviewsPage } from "./pages/ReviewsPage";

/**
 * Study, 2nd and 3rd entries: the reviews (spaced cards of the day, 15 minutes at most) and
 * the quizzes per module (SPEC 3.8 and 3.9).
 */
export function makeQuizManifest(GhostPanel?: ComponentType<QuizGhostProps>): FeatureManifest {
  return {
    id: "quiz",
    publicRoutes: [{ path: "/mobile", Component: MobilePage }],
    routes: [
      { path: "study/reviews", Component: ReviewsPage },
      { path: "study/quiz", Component: QuizIndexPage },
      { path: "study/quiz/:quizId", Component: () => createElement(QuizPage, { GhostPanel }) },
    ],
    nav: [
      { section: "study", labelKey: "quiz.nav.reviews", path: "/study/reviews", order: 2 },
      { section: "study", labelKey: "quiz.nav.quiz", path: "/study/quiz", order: 3 },
      { section: "study", labelKey: "mobile.title", path: "/mobile", order: 3.5 },
    ],
  };
}

export const quizManifest = makeQuizManifest();
