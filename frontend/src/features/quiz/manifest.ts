import { createElement, type ComponentType } from "react";
import { MobilePage } from "./pages/MobilePage";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import type { FeatureManifest } from "@/shared/lib/feature";
import { QuizIndexPage } from "./pages/QuizIndexPage";
import { QuizPage } from "./pages/QuizPage";
import { ReviewsPage } from "./pages/ReviewsPage";

/**
 * Étudier, 2e et 3e entrées : les révisions (fiches espacées du jour, 15 minutes au plus) et les
 * quiz par module (SPEC 3.8 et 3.9).
 */
export function makeQuizManifest(GhostPanel?: ComponentType<QuizGhostProps>): FeatureManifest {
  return {
    id: "quiz",
    publicRoutes: [{ path: "/mobile", Component: MobilePage }],
    routes: [
      { path: "etudier/revisions", Component: ReviewsPage },
      { path: "etudier/quiz", Component: QuizIndexPage },
      { path: "etudier/quiz/:quizId", Component: () => createElement(QuizPage, { GhostPanel }) },
    ],
    nav: [
      { section: "study", labelKey: "quiz.nav.reviews", path: "/etudier/revisions", order: 2 },
      { section: "study", labelKey: "quiz.nav.quiz", path: "/etudier/quiz", order: 3 },
      { section: "study", labelKey: "mobile.title", path: "/mobile", order: 3.5 },
    ],
  };
}

export const quizManifest = makeQuizManifest();
