import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonHuntPage } from "./pages/LessonHuntPage";

export const lessonHuntManifest: FeatureManifest = {
  id: "lesson_hunt",
  routes: [
    { path: "learn/lessons/:lessonId/errors", Component: LessonHuntPage },
    { path: "learn/error-hunts/:huntId", Component: LessonHuntPage },
  ],
};
