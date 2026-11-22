import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonVariantsPage } from "./pages/LessonVariantsPage";

export const lessonVariantsManifest: FeatureManifest = {
  id: "lesson_variants",
  routes: [{ path: "apprendre/variantes", Component: LessonVariantsPage }],
  nav: [{ section: "learn", labelKey: "lessonVariants.title", path: "/apprendre/variantes", order: 4.8 }],
};
