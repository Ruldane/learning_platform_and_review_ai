import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonHuntPage } from "./pages/LessonHuntPage";

export const lessonHuntManifest: FeatureManifest = {
  id: "lesson_hunt",
  routes: [
    { path: "apprendre/lecons/:lessonId/erreurs", Component: LessonHuntPage },
    { path: "apprendre/erreurs/:huntId", Component: LessonHuntPage },
  ],
};
