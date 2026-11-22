import type { FeatureManifest } from "@/shared/lib/feature";
import { ClassroomPage } from "./pages/ClassroomPage";
import { TrainingPage } from "./pages/TrainingPage";

export const conversationsManifest: FeatureManifest = {
  id: "conversations",
  routes: [
    { path: "etudier/training/:studyId?", Component: TrainingPage, handle: { wide: true } },
    { path: "apprendre/lecons/:lessonId/classe", Component: ClassroomPage },
  ],
  nav: [{ section: "study", labelKey: "training.title", path: "/etudier/training", order: 1.5 }],
};
