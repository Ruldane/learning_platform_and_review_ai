import type { FeatureManifest } from "@/shared/lib/feature";
import { SurpriseSettingsPage } from "./pages/SurpriseSettingsPage";

export const surpriseInterviewManifest: FeatureManifest = {
  id: "surprise_interview",
  routes: [{ path: "reglages/entretien-surprise", Component: SurpriseSettingsPage }],
  nav: [
    {
      section: "settings",
      labelKey: "surpriseInterview.title",
      path: "/reglages/entretien-surprise",
      order: 11,
    },
  ],
};
