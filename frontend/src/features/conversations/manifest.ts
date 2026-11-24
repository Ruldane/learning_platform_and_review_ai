import type { FeatureManifest } from "@/shared/lib/feature";
import { ClassroomPage } from "./pages/ClassroomPage";
import { FeynmanPage } from "./pages/FeynmanPage";
import { TrainingPage } from "./pages/TrainingPage";

export const conversationsManifest: FeatureManifest = {
  id: "conversations",
  routes: [
    { path: "study/training/:studyId?", Component: TrainingPage, handle: { wide: true } },
    { path: "learn/lessons/:lessonId/classroom", Component: ClassroomPage },
    { path: "learn/lessons/:lessonId/explain", Component: FeynmanPage },
    { path: "code/:sessionId/explain", Component: FeynmanPage },
    { path: "study/explain/:turnId", Component: FeynmanPage },
  ],
  nav: [{ section: "study", labelKey: "training.title", path: "/study/training", order: 1.5 }],
};
