import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonVariantsPage } from "./pages/LessonVariantsPage";

export const lessonVariantsManifest: FeatureManifest = {
  id: "lesson_variants",
  routes: [{ path: "learn/lesson-variants", Component: LessonVariantsPage }],
  nav: [
    {
      section: "learn",
      labelKey: "lessonVariants.title",
      path: "/learn/lesson-variants",
      order: 4.8,
    },
  ],
};
