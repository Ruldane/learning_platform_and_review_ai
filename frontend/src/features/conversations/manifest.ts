import type { FeatureManifest } from "@/shared/lib/feature";
import { ClassroomPage } from "./pages/ClassroomPage";
import { FeynmanPage } from "./pages/FeynmanPage";
import { TrainingPage } from "./pages/TrainingPage";

export const conversationsManifest: FeatureManifest = {
  id: "conversations",
  routes: [
    { path: "etudier/training/:studyId?", Component: TrainingPage, handle: { wide: true } },
    { path: "apprendre/lecons/:lessonId/classe", Component: ClassroomPage },
    { path: "apprendre/lecons/:lessonId/explique-moi", Component: FeynmanPage },
    { path: "code/:sessionId/explique-moi", Component: FeynmanPage },
    { path: "etudier/explique-moi/:turnId", Component: FeynmanPage },
  ],
  nav: [{ section: "study", labelKey: "training.title", path: "/etudier/training", order: 1.5 }],
};
